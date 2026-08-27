"""Append-only metric history.

Every run appends one flat JSON object to ``data/history.jsonl``.  That file is
the report's memory: it is what turns a snapshot into a trend, and it is what
the anomaly detector compares against.  JSON Lines was chosen over SQLite so the
history stays diffable in git and a scheduled job can commit it.
"""

from __future__ import annotations

import json
import os
from typing import Any, Iterable

from core import config

# Metrics carried into history.  Keeping this list explicit (rather than dumping
# the whole snapshot) keeps the file small and stops schema drift.
TRACKED_METRICS: tuple[str, ...] = (
    "tps", "non_vote_tps", "slot_time_ms", "epoch", "epoch_progress_pct",
    "block_height", "transaction_count", "vote_tx_share_pct",
    "validator_count", "delinquent_count", "delinquent_stake_pct",
    "nakamoto_coefficient", "top10_stake_pct", "total_stake_sol",
    "gossip_node_count", "dominant_client_pct", "distinct_client_count",
    "total_supply_sol", "circulating_supply_sol", "inflation_total_pct",
    "median_tx_fee_lamports", "median_priority_fee_lamports",
    "tx_failure_rate_pct", "priority_fee_share_pct",
    "avg_unique_payers_per_block", "unique_payers_in_sample",
    "price_usd", "market_cap_usd", "volume_24h_usd", "change_24h_pct",
    "tvl_usd", "defi_tvl_usd", "rwa_tvl_usd", "tokenized_equity_tvl_usd",
    "dex_volume_24h_usd", "chain_fees_24h_usd", "stablecoin_total_usd",
    "sources_ok", "sources_failed",
)


def load_history(path: str | None = None) -> list[dict[str, Any]]:
    """Read every well-formed record from the history file, oldest first.

    Malformed lines are skipped rather than fatal: a run interrupted mid-write
    must not permanently break the report.
    """
    path = path or config.HISTORY_PATH
    if not os.path.exists(path):
        return []
    records: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(record, dict) and record.get("ts"):
                records.append(record)
    records.sort(key=lambda r: r["ts"])
    return records


def append_record(record: dict[str, Any], path: str | None = None,
                  max_records: int | None = None) -> int:
    """Append ``record`` and trim the file to ``max_records``. Returns the count."""
    path = path or config.HISTORY_PATH
    max_records = max_records or config.HISTORY_MAX_RECORDS
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, separators=(",", ":"), sort_keys=True) + "\n")
    records = load_history(path)
    if len(records) > max_records:
        records = records[-max_records:]
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as handle:
            for item in records:
                handle.write(json.dumps(item, separators=(",", ":"), sort_keys=True) + "\n")
        os.replace(tmp, path)
    return len(records)


def build_record(timestamp: str, metrics: dict[str, Any]) -> dict[str, Any]:
    """Project the run's metric bag onto :data:`TRACKED_METRICS`."""
    record: dict[str, Any] = {"ts": timestamp}
    for key in TRACKED_METRICS:
        value = metrics.get(key)
        if isinstance(value, (int, float)) and value == value:  # drop NaN
            record[key] = round(value, 6) if isinstance(value, float) else value
    return record


def series(records: Iterable[dict[str, Any]], metric: str, window: int | None = None
           ) -> list[tuple[str, float]]:
    """Return the last ``window`` ``(timestamp, value)`` pairs for ``metric``."""
    window = window or config.BASELINE_WINDOW
    points = [
        (r["ts"], float(r[metric]))
        for r in records
        if isinstance(r.get(metric), (int, float))
    ]
    return points[-window:]
