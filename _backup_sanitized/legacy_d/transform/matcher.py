import pandas as pd
import logging
from typing import Dict

logger = logging.getLogger("WNBAPipeline")

class DataMatcher:
    """
    Aligns data from different sources (Team names, Player names, Dates).
    """

    def __init__(self, team_map_path: str, player_map_path: str):
        # In a real app, load these from JSON files
        self.team_map = {
            "Los Angeles Sparks": "LAS", "L.A. Sparks": "LAS", "LA": "LAS",
            "New York Liberty": "NYL", "NY": "NYL",
            "Las Vegas Aces": "LVA", "LV": "LVA",
            "Connecticut Sun": "CON", "CT": "CON",
            "Minnesota Lynx": "MIN",
            "Indiana Fever": "IND",
            "Phoenix Mercury": "PHO", "PHX": "PHO",
            "Seattle Storm": "SEA",
            "Dallas Wings": "DAL",
            "Chicago Sky": "CHI",
            "Atlanta Dream": "ATL",
            "Washington Mystics": "WAS"
        }
        self.player_map = {} # Load alias map

    def normalize_team(self, team_name_or_abbr: str) -> str:
        if not team_name_or_abbr:
            return "UNKNOWN"

        name = team_name_or_abbr.strip()

        # Explicit override for common names
        if "Minnesota" in name or "Lynx" in name: return "MIN"
        if "Indiana" in name or "Fever" in name: return "IND"
        if "Liberty" in name: return "NYL"
        if "Aces" in name: return "LVA"
        if "Sun" in name: return "CON"
        if "Storm" in name: return "SEA"
        if "Mercury" in name: return "PHO"
        if "Wings" in name: return "DAL"
        if "Sky" in name: return "CHI"
        if "Dream" in name: return "ATL"
        if "Mystics" in name: return "WAS"
        if "Sparks" in name: return "LAS"

        return self.team_map.get(name, name)

    def match_attendance_to_games(self, games_df: pd.DataFrame, attendance_df: pd.DataFrame) -> pd.DataFrame:
        """
        Joins official games with attendance data on Date + Home Team.
        """
        if games_df.empty or attendance_df.empty:
            return games_df

        # Normalize dates
        games_df['date_key'] = pd.to_datetime(games_df['game_date_utc']).dt.date
        attendance_df['date_key'] = pd.to_datetime(attendance_df['game_date_local']).dt.date

        # Normalize teams in attendance df
        attendance_df['home_abbr'] = attendance_df['home_team_name'].apply(self.normalize_team)

        # Merge
        # Note: We need to map games_df home_tid back to abbr or use a lookup.
        # For this snippet, assuming games_df has home_team_abbr or we can infer it.
        # Ideally, we join on (date, home_team_normalized).

        merged = pd.merge(
            games_df,
            attendance_df[['date_key', 'home_abbr', 'attendance']],
            left_on=['date_key', 'home_team_abbr'], # Assuming this col exists or is derived
            right_on=['date_key', 'home_abbr'],
            how='left',
            suffixes=('', '_att')
        )

        # Coalesce attendance
        if 'attendance_att' in merged.columns:
            merged['attendance'] = merged['attendance'].fillna(merged['attendance_att'])

        return merged

class SchemaBuilder:
    """
    Transforms raw extracted data into the final Warehouse Schema.
    """

    @staticmethod
    def build_fact_games(raw_games_df: pd.DataFrame) -> pd.DataFrame:
        # Transform logic here
        return raw_games_df

    @staticmethod
    def calculate_derived_metrics(games_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates rest days and back-to-back flags.
        """
        # Sort by team and date
        # Calculate diff between rows
        return games_df
