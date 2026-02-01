from abc import ABC, abstractmethod
import pandas as pd
import logging
import json
import os
import requests
from io import StringIO
from typing import Optional, Any
from src.utils.common import RequestUtils, IDGenerator

logger = logging.getLogger("WNBAPipeline")

class BaseExtractor(ABC):
    """Abstract base class for all data extractors."""
    def __init__(self, config):
        self.config = config
        self.raw_dir = "data_raw"
        os.makedirs(self.raw_dir, exist_ok=True)

    @abstractmethod
    def extract(self, season: int) -> pd.DataFrame:
        pass

class WNBAScheduleExtractor(BaseExtractor):
    """
    Extracts schedule via WNBA Data API, with fallbacks to ESPN and Basketball-Reference.
    """
    def extract(self, season: int) -> pd.DataFrame:
        # 1. Try WNBA Official Data API
        # url = f"https://data.wnba.com/data/10s/v2015/json/mobile_teams/wnba/{season}/league/00_full_schedule.json"
        # logger.info(f"Attempting WNBA Data API: {url}")
        # df = self._extract_from_api(url, season)
        # if not df.empty:
        #     return df

        # 2. Try ESPN (Often more reliable for scraping without strict anti-bot)
        logger.info("Attempting ESPN Schedule...")
        df = self._extract_from_espn(season)
        if not df.empty:
            return df

        # 3. Fallback: Basketball-Reference
        logger.warning("ESPN failed. Falling back to Basketball-Reference...")
        return self._extract_from_bball_ref(season)

    def _extract_from_api(self, url: str, season: int) -> pd.DataFrame:
        try:
            response = RequestUtils.get(url)
            if not response: return pd.DataFrame()

            data = response.json()
            games = []
            lscd = data.get('lscd', [])
            for item in lscd:
                mscd = item.get('mscd', {})
                game_list = mscd.get('g', [])
                for g in game_list:
                    gid = IDGenerator.generate_id("wnba", g['gid'])
                    home_stats = g.get('h', {})
                    away_stats = g.get('v', {})
                    games.append({
                        'gid': gid,
                        'provider_game_id': g['gid'],
                        'season_year': season,
                        'game_date_utc': f"{g.get('gdte')}T{g.get('etm', '00:00:00')}",
                        'home_tid': IDGenerator.generate_id("wnba", home_stats.get('tid')),
                        'away_tid': IDGenerator.generate_id("wnba", away_stats.get('tid')),
                        'home_team_abbr': home_stats.get('ta'),
                        'away_team_abbr': away_stats.get('ta'),
                        'home_score': home_stats.get('s'),
                        'away_score': away_stats.get('s'),
                        'venue_name': g.get('an'),
                        'venue_city': g.get('ac'),
                        'status': g.get('stt'),
                        'source': 'wnba_data_api'
                    })
            return pd.DataFrame(games)
        except Exception:
            return pd.DataFrame()

    def _extract_from_espn(self, season: int) -> pd.DataFrame:
        # ESPN structure usually: https://www.espn.com/wnba/schedule/_/season/{season}
        url = f"https://www.espn.com/wnba/schedule/_/season/{season}"
        try:
            response = RequestUtils.get(url)
            if not response: return pd.DataFrame()

            # Pandas read_html is very good at ESPN tables
            dfs = pd.read_html(StringIO(response.text))

            games = []
            for df in dfs:
                # ESPN tables usually have 'Matchup', 'Result', 'Time', 'TV' or similar
                # Or sometimes just columns 0, 1, 2
                if 'Matchup' in df.columns:
                    for idx, row in df.iterrows():
                        matchup = row['Matchup']
                        # Format: "Team A at Team B" or "Team A vs Team B"
                        home, away = "Unknown", "Unknown"
                        if " at " in str(matchup):
                            away, home = str(matchup).split(" at ", 1)
                        elif " vs " in str(matchup):
                            home, away = str(matchup).split(" vs ", 1)
                        else:
                            # Sometimes just team names
                            continue

                        # Date is usually in a preceding row or column, simpler extraction might miss exact date
                        # For this heuristics, we might skip exact date if not easily parsable,
                        # or assume the table header contains the date (ESPN does this tricky grouping)

                        # Simplified: Just getting the match list
                        gid = IDGenerator.generate_id("espn", f"{season}_{matchup}_{idx}")

                        games.append({
                            'gid': gid,
                            'provider_game_id': f"espn_{idx}",
                            'season_year': season,
                            'game_date_utc': f"{season}-01-01", # Placeholder, ESPN HTML date parsing is complex
                            'home_team_abbr': home.strip(),
                            'away_team_abbr': away.strip(),
                            'home_score': 0,
                            'away_score': 0,
                            'status': 'Scheduled',
                            'source': 'espn_html'
                        })

            if games:
                logger.info(f"Extracted {len(games)} games from ESPN")
                return pd.DataFrame(games)
            return pd.DataFrame()

        except Exception as e:
            logger.error(f"ESPN extraction failed: {e}")
            return pd.DataFrame()

    def _extract_from_bball_ref(self, season: int) -> pd.DataFrame:
        url = f"https://www.basketball-reference.com/wnba/years/{season}_games.html"
        logger.info(f"Scraping {url}")

        try:
            response = RequestUtils.get(url)
            if not response:
                return pd.DataFrame()

            dfs = pd.read_html(StringIO(response.text))
            full_df = pd.DataFrame()
            for df in dfs:
                if 'Date' in df.columns and ('Visitor' in df.columns or 'Away' in df.columns):
                    full_df = pd.concat([full_df, df], ignore_index=True)

            if full_df.empty:
                return pd.DataFrame()

            full_df = full_df[full_df['Date'] != 'Date'] # Remove headers

            games = []
            for _, row in full_df.iterrows():
                home_col = 'Home' if 'Home' in row else 'Home/Neutral'
                visitor_col = 'Visitor' if 'Visitor' in row else 'Visitor/Neutral'

                home_team = row.get(home_col)
                away_team = row.get(visitor_col)

                if pd.isna(home_team) or pd.isna(away_team): continue

                raw_id = f"{season}_{row['Date']}_{home_team}"
                gid = IDGenerator.generate_id("bballref", raw_id)

                h_score = row.get('PTS.1')
                v_score = row.get('PTS')

                # Check if Played
                status = 'Completed' if pd.notna(h_score) else 'Scheduled'

                games.append({
                    'gid': gid,
                    'provider_game_id': raw_id,
                    'season_year': season,
                    'game_date_utc': row['Date'],
                    'home_team_abbr': home_team,
                    'away_team_abbr': away_team,
                    'home_score': h_score,
                    'away_score': v_score,
                    'status': status,
                    'source': 'bball_ref_html'
                })

            return pd.DataFrame(games)

        except Exception as e:
            logger.error(f"BBallRef Extraction Error: {e}")
            return pd.DataFrame()

class TeamSpecificExtractor(BaseExtractor):
    """
    Specific extraction for team analysis (e.g. Minnesota Lynx).
    """
    def extract(self, season: int) -> pd.DataFrame:
        # Implement abstract method by defaulting to MIN roster
        return self.extract_roster(season, "MIN")

    def extract_roster(self, season: int, team_abbr="MIN") -> pd.DataFrame:
        # Basketball Reference Team Page
        url = f"https://www.basketball-reference.com/wnba/teams/{team_abbr}/{season}.html"
        logger.info(f"Extracting {team_abbr} stats from {url}")

        try:
            response = RequestUtils.get(url)
            if not response: return pd.DataFrame()

            dfs = pd.read_html(StringIO(response.text))

            # Roster usually has 'Player', 'Pos', 'Ht', 'Wt', 'Birth Date', 'Exp', 'College'
            roster_df = pd.DataFrame()
            for df in dfs:
                if 'Player' in df.columns and 'Pos' in df.columns:
                    roster_df = df
                    break

            if not roster_df.empty:
                roster_df['season'] = season
                roster_df['team'] = team_abbr
                roster_df['source'] = 'bball_ref_team'
                return roster_df

        except Exception as e:
            logger.error(f"Team roster extract failed: {e}")

        return pd.DataFrame()

class AttendanceExtractor(BaseExtractor):
    def extract(self, season: int) -> pd.DataFrame:
        url = self.config['acrossthetimeline']['attendance']
        logger.info(f"Parsing attendance from {url}")
        try:
            response = RequestUtils.get(url)
            if not response: return pd.DataFrame()

            dfs = pd.read_html(StringIO(response.text))
            target_df = pd.DataFrame()
            for df in dfs:
                if 'Date' in df.columns and 'Attendance' in df.columns:
                    target_df = df
                    break

            if not target_df.empty:
                target_df = target_df.rename(columns={
                    'Date': 'game_date_local',
                    'Home Team': 'home_team_name',
                    'Attendance': 'attendance'
                })
                target_df = target_df[target_df['game_date_local'].astype(str).str.contains(str(season))]
                target_df['source'] = 'acrossthetimeline_html'
                return target_df
        except Exception:
            pass
        return pd.DataFrame()

class SalaryExtractor(BaseExtractor):
    def extract(self, season: int) -> pd.DataFrame:
        url = self.config['herhoopstats']['cap_summary'].format(season=season)
        logger.info(f"Fetching salaries from {url}")
        try:
            response = RequestUtils.get(url)
            if not response: return pd.DataFrame()

            dfs = pd.read_html(StringIO(response.text))
            salary_df = pd.DataFrame()
            for df in dfs:
                if 'Player' in df.columns and any('Cap' in c for c in df.columns):
                    salary_df = df
                    break

            if not salary_df.empty:
                salary_df['season_year'] = season
                salary_df['source'] = 'herhoopstats_html'
                return salary_df
        except Exception:
            pass
        return pd.DataFrame()
