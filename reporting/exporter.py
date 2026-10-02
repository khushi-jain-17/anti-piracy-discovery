import json
import logging
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd
from config import settings

logger = logging.getLogger(__name__)

MANDATORY_FIELDS = [
    "search_engine",
    "query",
    "rank",
    "url",
    "domain",
    "classification",
    "confidence_score",
    "player_detected",
    "player_type",
    "player_status",
    "stream_source",
    "screenshot_path",
    "checked_at_utc",
    "hosting_ip"
]

class ReportExporter:
    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or settings.OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_csv(self, records: List[Dict[str, Any]], filename: str = "report.csv") -> Path:
        filepath = self.output_dir / filename
        try:
            # Filter and order mandatory fields, keeping extra fields in full list
            df = pd.DataFrame(records)
            if not df.empty:
                cols = [c for c in MANDATORY_FIELDS if c in df.columns] + [c for c in df.columns if c not in MANDATORY_FIELDS]
                df = df[cols]
            df.to_csv(filepath, index=False, encoding="utf-8")
            logger.info(f"[Exporter] CSV report saved to: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"[Exporter] CSV export failed: {e}")
            return filepath

    def export_json(self, records: List[Dict[str, Any]], filename: str = "report.json") -> Path:
        filepath = self.output_dir / filename
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=2, ensure_ascii=False)
            logger.info(f"[Exporter] JSON report saved to: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"[Exporter] JSON export failed: {e}")
            return filepath

    def export_pirates_only(self, records: List[Dict[str, Any]], csv_filename: str = "report_pirates.csv", json_filename: str = "report_pirates.json") -> Dict[str, Path]:
        """Export pirate output strictly excluding allowlisted/official domains."""
        pirate_records = [r for r in records if r.get("classification") in ["Pirate", "Uncertain"]]
        csv_path = self.export_csv(pirate_records, filename=csv_filename)
        json_path = self.export_json(pirate_records, filename=json_filename)
        logger.info(f"[Exporter] Exported {len(pirate_records)} non-allowlisted pirate records to pirate output files.")
        return {"csv": csv_path, "json": json_path}

