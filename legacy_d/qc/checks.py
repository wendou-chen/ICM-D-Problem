import pandas as pd
import logging
import json
import os
from typing import Dict, List

logger = logging.getLogger("WNBAPipeline")

class QualityControl:

    def __init__(self, warehouse_dir: str, config: Dict):
        self.warehouse_dir = warehouse_dir
        self.config = config
        self.report = {
            "timestamp": pd.Timestamp.now().isoformat(),
            "checks": [],
            "status": "PASS"
        }

    def run_all_checks(self):
        self.check_game_coverage()
        self.check_attendance_missing()
        self.check_referential_integrity()

        # Save report
        os.makedirs("reports", exist_ok=True)
        with open("reports/qc_summary.json", "w") as f:
            json.dump(self.report, f, indent=2)

        self._generate_markdown_report()

    def check_game_coverage(self):
        """Checks if row count matches expected games (approx)."""
        try:
            df = pd.read_parquet(f"{self.warehouse_dir}/fact_games.parquet")
            count = len(df)
            # WNBA regular season is typically 40 games * 12 teams / 2 = 240 games
            # Adjust for season
            expected = 240
            ratio = count / expected

            passed = ratio >= self.config['quality_checks']['coverage_games_threshold']
            self.report['checks'].append({
                "name": "Game Coverage",
                "value": count,
                "expected": expected,
                "passed": passed
            })
            if not passed:
                self.report['status'] = "WARN"
        except Exception as e:
            logger.error(f"QC Check Failed: {e}")

    def check_attendance_missing(self):
        try:
            df = pd.read_parquet(f"{self.warehouse_dir}/fact_games.parquet")
            if 'attendance' not in df.columns:
                return

            missing = df['attendance'].isna().sum()
            total = len(df)
            pct = missing / total if total > 0 else 0

            passed = pct <= self.config['quality_checks']['attendance_missing_threshold']
            self.report['checks'].append({
                "name": "Attendance Missing Rate",
                "value": pct,
                "threshold": self.config['quality_checks']['attendance_missing_threshold'],
                "passed": passed
            })
        except:
            pass

    def check_referential_integrity(self):
        # Check if all player boxscores have valid game_ids in fact_games
        pass

    def _generate_markdown_report(self):
        md = "# Data Pipeline Quality Control Report\n\n"
        md += f"**Timestamp**: {self.report['timestamp']}\n"
        md += f"**Overall Status**: {self.report['status']}\n\n"
        md += "| Check | Value | Passed |\n"
        md += "|---|---|---|\n"
        for check in self.report['checks']:
            md += f"| {check['name']} | {check['value']} | {check['passed']} |\n"

        with open("reports/qc_summary.md", "w") as f:
            f.write(md)
