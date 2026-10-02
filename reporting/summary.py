import logging
from typing import List, Dict, Any
from tabulate import tabulate
from config import settings

logger = logging.getLogger(__name__)

class SummaryReporter:
    @staticmethod
    def generate_summary(records: List[Dict[str, Any]]) -> Dict[str, Any]:
        total_discovered = len(records)
        total_official = sum(1 for r in records if r.get("classification") == "Official")
        total_pirate = sum(1 for r in records if r.get("classification") == "Pirate")
        total_uncertain = sum(1 for r in records if r.get("classification") == "Uncertain")
        
        player_detected_count = sum(1 for r in records if r.get("player_detected") is True)
        actively_playing_count = sum(1 for r in records if r.get("player_status") == "Player Present - Playing")

        # Top pirate domains
        pirate_domains: Dict[str, int] = {}
        for r in records:
            if r.get("classification") == "Pirate":
                dom = r.get("domain", "")
                pirate_domains[dom] = pirate_domains.get(dom, 0) + 1

        top_pirate_domains = sorted(pirate_domains.items(), key=lambda x: x[1], reverse=True)[:5]

        summary = {
            "total_discovered": total_discovered,
            "total_official": total_official,
            "total_pirate": total_pirate,
            "total_uncertain": total_uncertain,
            "players_detected": player_detected_count,
            "actively_playing": actively_playing_count,
            "top_pirate_domains": top_pirate_domains
        }

        # Save summary report to Markdown file
        summary_md_path = settings.OUTPUT_DIR / "summary.md"
        try:
            with open(summary_md_path, "w", encoding="utf-8") as f:
                f.write("# DAZN Anti-Piracy Discovery & Verification Summary Report\n\n")
                f.write(f"- **Total URLs Discovered:** {total_discovered}\n")
                f.write(f"- **Official / Authorised Domains:** {total_official}\n")
                f.write(f"- **Suspected Pirate Domains:** {total_pirate}\n")
                f.write(f"- **Uncertain Domains:** {total_uncertain}\n")
                f.write(f"- **Video Players Detected:** {player_detected_count}\n")
                f.write(f"- **Actively Playing Streams:** {actively_playing_count}\n\n")
                if top_pirate_domains:
                    f.write("### Top Confirmed Pirate Domains\n\n")
                    f.write("| Domain | Frequency |\n| --- | --- |\n")
                    for dom, count in top_pirate_domains:
                        f.write(f"| `{dom}` | {count} |\n")
            logger.info(f"[SummaryReporter] Saved summary report to: {summary_md_path}")
        except Exception as e:
            logger.error(f"[SummaryReporter] Failed to save summary.md: {e}")

        # Print summary to console
        print("\n" + "=" * 65)
        print("         ANTI-PIRACY DISCOVERY & VERIFICATION SUMMARY REPORT      ")
        print("=" * 65)
        
        table_data = [
            ["Total URLs Discovered", total_discovered],
            ["Official / Authorised Domains", total_official],
            ["Suspected Pirate Domains", total_pirate],
            ["Uncertain Domains", total_uncertain],
            ["Video Players Detected", player_detected_count],
            ["Actively Playing Streams", actively_playing_count],
        ]
        try:
            print(tabulate(table_data, headers=["Metric", "Count"], tablefmt="grid"))
        except Exception:
            for k, v in table_data:
                print(f"  {k}: {v}")

        if top_pirate_domains:
            print("\nTop Confirmed Pirate Domains:")
            top_table = [[dom, count] for dom, count in top_pirate_domains]
            try:
                print(tabulate(top_table, headers=["Domain", "Frequency"], tablefmt="grid"))
            except Exception:
                for dom, count in top_table:
                    print(f"  {dom}: {count}")
        print("=" * 65 + "\n")

        return summary

