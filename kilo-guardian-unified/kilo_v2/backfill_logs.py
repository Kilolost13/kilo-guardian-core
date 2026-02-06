"""Historical Caddy Log Backfill

Purpose:
    Retroactively process existing Caddy access log(s) to:
      1. Normalize legacy non-JSON lines to structured JSON.
      2. Re-run attack detection patterns for missed historical events.
      3. (Optionally) enrich source IPs if enrichment enabled.
      4. Produce normalized JSONL output and an attack summary JSON.

Outputs:
    kilo_data/security_logs/caddy_backfill_normalized.jsonl  (all normalized entries)
    kilo_data/security_logs/caddy_backfill_attacks.json      (list of detected attacks)
    kilo_data/security_logs/caddy_backfill_stats.json        (summary counts)

Usage:
    python -m kilo_v2.backfill_logs --input /path/to/caddy_access.log
    python -m kilo_v2.backfill_logs --input logs/caddy_access.log --attacks-only

Flags:
    --input <file>       Path to legacy log file (default from config.CADDY_LOG_PATH)
    --attacks-only       Only write attack events (skip full normalized JSONL)
    --limit <N>          Stop after processing first N lines (for testing)

Idempotency:
    Running multiple times overwrites output files; use versioning externally if desired.

Performance:
    Stream reads the log file line-by-line (no full file read into memory).

"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger("Backfill")
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)

try:
    from . import config
    from .security_monitor import CaddyLogParser
except Exception:
    # Allow running as script from repo root
    import config  # type: ignore
    from security_monitor import CaddyLogParser  # type: ignore

# Optional enrichment
_ENRICH = getattr(config, "ENABLE_IP_ENRICHMENT", False)
if _ENRICH:
    try:
        from .ip_enrichment import enrich_ip
    except Exception:
        from ip_enrichment import enrich_ip  # type: ignore
else:

    def enrich_ip(ip: str):  # type: ignore
        return {"ip": ip, "enabled": False}


DEFAULT_OUT_DIR = Path("kilo_data/security_logs")
DEFAULT_OUT_DIR.mkdir(parents=True, exist_ok=True)


def process_line(parser: CaddyLogParser, line: str):
    """Return tuple(normalized_entry or None, attack_dict or None)."""
    line = line.strip()
    if not line:
        return None, None
    # Attempt to parse as attack
    attack = parser.parse_log_line(line)
    normalized = None
    try:
        # If already JSON leave as is; else try normalization regex branch inside parser again.
        try:
            normalized = json.loads(line)
        except Exception:
            # The parser's normalization logic only returns attacks; we replicate minimal legacy normalization here.
            import re

            candidate = line
            if candidate.startswith("{") and candidate.endswith("}"):
                candidate = re.sub(r"(\b[\w.-]+)=", r'"\1":', candidate)
                candidate = re.sub(r':(?!\s*["])([^\s{},]+)', r':"\1"', candidate)
                candidate = candidate.replace("'", '"')
                try:
                    normalized = json.loads(candidate)
                except Exception:
                    normalized = {"raw": line, "parse_error": True}
            else:
                normalized = {"raw": line, "parse_error": True}
    except Exception:
        normalized = {"raw": line, "parse_error": True}
    return normalized, attack


def run_backfill(
    input_path: Path, attacks_only: bool = False, limit: int | None = None
):
    parser = CaddyLogParser()
    attacks: List[Dict] = []
    total_lines = 0
    attack_counts = {}

    normalized_path = DEFAULT_OUT_DIR / "caddy_backfill_normalized.jsonl"
    attacks_path = DEFAULT_OUT_DIR / "caddy_backfill_attacks.json"
    stats_path = DEFAULT_OUT_DIR / "caddy_backfill_stats.json"

    if not attacks_only:
        if normalized_path.exists():
            normalized_path.unlink()
        norm_f = normalized_path.open("w", encoding="utf-8")
    else:
        norm_f = None

    with input_path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            total_lines += 1
            if limit and total_lines > limit:
                break
            normalized, attack = process_line(parser, line)
            if attack:
                # Attach enrichment
                if _ENRICH:
                    attack["enrichment"] = enrich_ip(attack.get("ip", "unknown"))
                attacks.append(attack)
                attack_type = attack.get("type", "unknown")
                attack_counts[attack_type] = attack_counts.get(attack_type, 0) + 1
            if not attacks_only and normalized is not None:
                try:
                    norm_f.write(json.dumps(normalized) + "\n")
                except Exception:
                    pass
    if norm_f:
        norm_f.close()

    # Write attacks
    with attacks_path.open("w", encoding="utf-8") as af:
        json.dump(attacks, af, indent=2)

    stats = {
        "input_file": str(input_path),
        "lines_processed": total_lines,
        "attacks_detected": len(attacks),
        "by_type": attack_counts,
        "enrichment_enabled": _ENRICH,
        "timestamp": __import__("datetime").datetime.now().isoformat(),
    }
    with stats_path.open("w", encoding="utf-8") as sf:
        json.dump(stats, sf, indent=2)

    logger.info(f"Backfill complete: {total_lines} lines, {len(attacks)} attacks.")
    logger.info(f"Attack types: {attack_counts}")
    logger.info(
        f"Outputs: {attacks_path} and {stats_path}{'' if attacks_only else ' plus ' + str(normalized_path)}"
    )


def main(argv=None):
    ap = argparse.ArgumentParser(description="Historical Caddy log backfill")
    ap.add_argument(
        "--input",
        type=str,
        default=getattr(config, "CADDY_LOG_PATH", "logs/caddy_access.log"),
        help="Path to legacy Caddy log file",
    )
    ap.add_argument(
        "--attacks-only",
        action="store_true",
        help="Only write attack events (skip full normalized JSONL)",
    )
    ap.add_argument("--limit", type=int, help="Process only first N lines (testing)")
    args = ap.parse_args(argv)

    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"Input log does not exist: {input_path}")
        return 2

    run_backfill(input_path, attacks_only=args.attacks_only, limit=args.limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
