"""Machine-readable JSON output.

Two shapes are written:

* ``report.json`` - the full snapshot: metrics, every section, alerts, the
  source ledger and the anomaly-detector diagnostics.
* ``latest.json`` - a small, stable summary intended for polling by other
  services (status badge, bot, uptime check).  Keeping it separate means the
  large report can change shape without breaking machine consumers.
"""

from __future__ import annotations

import json
import os
from typing import Any


def _clean(value: Any) -> Any:
    """Recursively drop private keys and coerce non-serialisable values."""
    if isinstance(value, dict):
        return {k: _clean(v) for k, v in value.items() if not k.startswith("_")}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    if isinstance(value, set):
        return sorted(value)
    if isinstance(value, float) and value != value:  # NaN
        return None
    return value


def build_latest(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Small polling summary derived from the full snapshot."""
    metrics = snapshot.get("metrics", {})
    counts = snapshot.get("anomaly_detection", {}).get("counts", {})
    keys = (
        "tps", "non_vote_tps", "slot_time_ms", "epoch", "epoch_progress_pct",
        "validator_count", "delinquent_count", "delinquent_stake_pct",
        "nakamoto_coefficient", "price_usd", "market_cap_usd", "tvl_usd",
        "dex_volume_24h_usd", "chain_fees_24h_usd", "stablecoin_total_usd",
        "median_tx_fee_lamports", "tx_failure_rate_pct", "staking_ratio_pct",
    )
    return {
        "generated_at": snapshot.get("generated_at"),
        "schema_version": snapshot.get("schema_version"),
        "status": (
            "critical" if counts.get("critical") else
            "warning" if counts.get("warning") else "ok"
        ),
        "alerts": counts,
        "sources": snapshot.get("source_summary"),
        "history_records": snapshot.get("history", {}).get("records"),
        "metrics": {k: metrics.get(k) for k in keys if metrics.get(k) is not None},
    }


def write(snapshot: dict[str, Any], out_dir: str) -> list[str]:
    """Write ``report.json`` and ``latest.json``; return the paths written."""
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    full = os.path.join(out_dir, "report.json")
    with open(full, "w", encoding="utf-8") as handle:
        json.dump(_clean(snapshot), handle, indent=2, sort_keys=False, default=str)
        handle.write("\n")
    paths.append(full)

    latest = os.path.join(out_dir, "latest.json")
    with open(latest, "w", encoding="utf-8") as handle:
        json.dump(build_latest(snapshot), handle, indent=2, default=str)
        handle.write("\n")
    paths.append(latest)
    return paths
