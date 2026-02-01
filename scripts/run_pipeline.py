import argparse
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import yaml
import logging
import pandas as pd
from src.extractors.base_extractors import WNBAScheduleExtractor, AttendanceExtractor, SalaryExtractor, TeamSpecificExtractor
from src.extractors.pdf_extractor import TVBDMAExtractor
from src.transform.matcher import DataMatcher, SchemaBuilder
from src.qc.checks import QualityControl

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("WNBAPipeline")

def load_config():
    with open("configs/sources.yaml", "r", encoding='utf-8') as f:
        sources = yaml.safe_load(f)
    with open("configs/schema.yaml", "r", encoding='utf-8') as f:
        schema = yaml.safe_load(f)
    return sources, schema

def main():
    parser = argparse.ArgumentParser(description="WNBA Data Pipeline")
    parser.add_argument("--seasons", nargs="+", type=int, default=[2024], help="Seasons to process")
    parser.add_argument("--skip_pdf", action="store_true", help="Skip PDF extraction")
    args = parser.parse_args()

    sources_conf, schema_conf = load_config()

    schedule_ext = WNBAScheduleExtractor(sources_conf)
    attendance_ext = AttendanceExtractor(sources_conf)
    salary_ext = SalaryExtractor(sources_conf)
    dma_ext = TVBDMAExtractor(sources_conf)
    team_ext = TeamSpecificExtractor(sources_conf) # New Extractor

    if not os.path.exists("configs/team_name_mapping.json"):
        with open("configs/team_name_mapping.json", "w") as f: f.write("{}")

    matcher = DataMatcher("configs/team_name_mapping.json", "configs/player_name_mapping.json")

    all_games = []

    for season in args.seasons:
        logger.info(f"=== Processing Season {season} ===")

        # 1. Games (Enhanced Fallback)
        games_df = schedule_ext.extract(season)
        if games_df.empty:
            logger.warning(f"No games found for {season}. Check extractors.")
        else:
            logger.info(f"Extracted {len(games_df)} games.")

        # 2. Attendance
        att_df = attendance_ext.extract(season)

        # 3. Salaries
        salaries = salary_ext.extract(season)
        if not salaries.empty:
            salaries.to_parquet(f"data_warehouse/fact_salaries_{season}.parquet", index=False)

        # 4. Join
        if not games_df.empty:
            if 'home_team_abbr' not in games_df.columns:
                games_df['home_team_abbr'] = games_df['home_tid'].apply(lambda x: "UNK")

            merged = matcher.match_attendance_to_games(games_df, att_df)
            all_games.append(merged)

        # 5. Team Specific (Lynx)
        # Specifically fetch Minnesota Lynx (MIN) Roster/Stats
        logger.info(f"Extracting Minnesota Lynx (MIN) data for {season}...")
        lynx_roster = team_ext.extract_roster(season, "MIN")
        if not lynx_roster.empty:
            lynx_file = f"data_warehouse/minnesota_lynx_{season}_roster.csv"
            lynx_roster.to_csv(lynx_file, index=False)
            logger.info(f"Saved Lynx roster to {lynx_file}")
        else:
            logger.warning("Could not fetch Lynx roster.")

    # Save Global
    if all_games:
        final_df = pd.concat(all_games, ignore_index=True)
        final_df.to_parquet("data_warehouse/fact_games.parquet", index=False)
        final_df.to_csv("data_warehouse/fact_games.csv", index=False)

        logger.info("Running QC...")
        qc = QualityControl("data_warehouse", schema_conf)
        qc.run_all_checks()

    logger.info("Pipeline Finished.")

if __name__ == "__main__":
    main()
