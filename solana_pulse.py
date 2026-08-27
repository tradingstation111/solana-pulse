#!/usr/bin/env python3
"""Solana Pulse - an auto-updating report on the state of the Solana ecosystem.

Collects on-chain and off-chain data from public, keyless sources, checks it
against its own recorded history for anomalies, and writes three outputs:

    out/index.html   interactive dark-theme dashboard, entirely self-contained
    out/report.md    human-readable Markdown report
    out/report.json  full machine-readable snapshot (plus out/latest.json)

Dependencies: the Python standard library. Nothing else. No API keys.

Usage
-----
    python3 solana_pulse.py                    one run
    python3 solana_pulse.py --interval 30m     run forever, every 30 minutes
    python3 solana_pulse.py --out docs         write somewhere else
    python3 solana_pulse.py --no-blocks        skip block sampling (less bandwidth)
    python3 solana_pulse.py --quiet            only print errors
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
import traceback
from typing import Any

from core import config, pipeline
from render import html as html_renderer, jsonout, markdown as md_renderer

VERSION = "1.0.0"
_DURATION = re.compile(r"^(\d+(?:\.\d+)?)\s*([smhd]?)$", re.IGNORECASE)
_UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400, "": 60}


def parse_interval(text: str) -> float:
    """Parse '90s', '30m', '2h', '1d' or a bare number of minutes into seconds."""
    match = _DURATION.match(text.strip())
    if not match:
        raise argparse.ArgumentTypeError(
            f"invalid interval {text!r}; use forms like 90s, 30m, 2h, 1d")
    seconds = float(match.group(1)) * _UNITS[match.group(2).lower()]
    if seconds < 60:
        raise argparse.ArgumentTypeError("interval must be at least 60 seconds")
    return seconds


def build_parser() -> argparse.ArgumentParser:
    """Command-line interface."""
    parser = argparse.ArgumentParser(
        prog="solana_pulse.py",
        description="Generate the Solana ecosystem report (HTML, Markdown, JSON).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  python3 solana_pulse.py\n"
               "  python3 solana_pulse.py --interval 30m --out docs\n"
               "  python3 solana_pulse.py --no-blocks --quiet\n",
    )
    parser.add_argument("--out", default="out", metavar="DIR",
                        help="output directory for the generated files (default: out)")
    parser.add_argument("--history", default=config.HISTORY_PATH, metavar="PATH",
                        help=f"append-only metric history (default: {config.HISTORY_PATH})")
    parser.add_argument("--interval", type=parse_interval, metavar="DURATION",
                        help="run continuously, waiting this long between runs (e.g. 30m)")
    parser.add_argument("--runs", type=int, default=0, metavar="N",
                        help="with --interval, stop after N runs (default: run forever)")
    parser.add_argument("--no-blocks", action="store_true",
                        help="skip raw block sampling; faster and much less bandwidth")
    parser.add_argument("--blocks", type=int, metavar="N",
                        help=f"number of blocks to sample (default: {config.BLOCK_SAMPLE_COUNT})")
    parser.add_argument("--quiet", action="store_true", help="only report errors")
    parser.add_argument("--version", action="version", version=f"Solana Pulse {VERSION}")
    return parser


def generate(args: argparse.Namespace) -> dict[str, Any]:
    """Run the pipeline once and write every output. Returns the snapshot."""
    config.HISTORY_PATH = args.history
    if args.blocks:
        config.BLOCK_SAMPLE_COUNT = max(1, args.blocks)

    log = (lambda *a: None) if args.quiet else (lambda *a: print(*a, flush=True))
    started = time.time()
    log(f"Solana Pulse {VERSION} — collecting from public keyless sources…")

    snapshot = pipeline.run(sample_blocks=not args.no_blocks)

    summary = snapshot["source_summary"]
    log(f"  sources: {summary['ok']}/{summary['total']} live"
        + (f" — degraded: {', '.join(summary['degraded'])}" if summary["degraded"] else ""))
    counts = snapshot["anomaly_detection"]["counts"]
    log(f"  alerts:  {counts['total']} "
        f"({counts['critical']} critical, {counts['warning']} warning, {counts['info']} info)")
    log(f"  history: {snapshot['history']['records']} runs in {snapshot['history']['path']}")

    html_path = html_renderer.write(snapshot, args.out)
    md_path = md_renderer.write(snapshot, args.out)
    json_paths = jsonout.write(snapshot, args.out)
    for path in [html_path, md_path, *json_paths]:
        log(f"  wrote {path} ({os.path.getsize(path):,} bytes)")
    log(f"Done in {time.time() - started:.1f}s.")
    return snapshot


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns a process exit code."""
    args = build_parser().parse_args(argv)
    if not args.interval:
        try:
            snapshot = generate(args)
        except Exception:  # noqa: BLE001 - report the failure, do not dump a bare trace
            traceback.print_exc()
            print("Report generation failed. No output was written.", file=sys.stderr)
            return 1
        return 2 if snapshot["source_summary"]["ok"] == 0 else 0

    runs = 0
    while True:
        try:
            generate(args)
        except KeyboardInterrupt:
            print("\nStopped.")
            return 0
        except Exception:  # noqa: BLE001 - a scheduled loop must survive one bad run
            traceback.print_exc()
            print("Run failed; continuing to the next interval.", file=sys.stderr)
        runs += 1
        if args.runs and runs >= args.runs:
            return 0
        if not args.quiet:
            print(f"Sleeping {args.interval / 60:.0f} min until the next run…", flush=True)
        try:
            time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nStopped.")
            return 0


if __name__ == "__main__":
    sys.exit(main())
