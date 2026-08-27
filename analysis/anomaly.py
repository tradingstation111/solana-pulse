"""Anomaly detection over the metric history and the current snapshot.

Three independent detectors run on every report:

1. **Robust statistical outliers.**  For each watched metric the modified
   z-score ``0.6745 * (x - median) / MAD`` is computed over the rolling
   history window.  Median and MAD are used instead of mean and standard
   deviation because a single earlier spike would otherwise inflate the
   baseline and mask the next one.  Metrics can be one-sided: a *rising*
   Nakamoto coefficient is good news and should never raise an alert.

2. **Absolute threshold rules.**  Statistics cannot flag a condition that has
   simply always been true - a permanently unhealthy cluster has a healthy
   baseline.  Fixed rules cover the states that are bad regardless of history.

3. **Cross-source correlation.**  Signals that only exist because the report
   holds several sources at once: price moving without TVL following, DEX
   volume spiking while fees do not, throughput rising while the failure rate
   rises with it.  These are the checks a single-source dashboard cannot make.

Until :data:`core.config.MIN_BASELINE_POINTS` runs have accumulated, detector 1
reports "baseline building" instead of firing, so a fresh deployment does not
open with false positives.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Any, Literal

from core import config

Severity = Literal["info", "warning", "critical"]
SEVERITY_ORDER = {"critical": 0, "warning": 1, "info": 2}


@dataclass
class Alert:
    """One detected condition, ready for HTML, Markdown and JSON output."""

    severity: Severity
    metric: str
    title: str
    detail: str
    value: float | None = None
    baseline: float | None = None
    z_score: float | None = None
    detector: str = "threshold"
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """JSON-serialisable form with floats rounded for readability."""
        return {
            "severity": self.severity,
            "metric": self.metric,
            "title": self.title,
            "detail": self.detail,
            "value": round(self.value, 4) if isinstance(self.value, float) else self.value,
            "baseline": round(self.baseline, 4) if isinstance(self.baseline, float) else self.baseline,
            "z_score": round(self.z_score, 2) if self.z_score is not None else None,
            "detector": self.detector,
            "tags": self.tags,
        }


@dataclass(frozen=True)
class Watch:
    """Declares how one metric is monitored statistically."""

    metric: str
    label: str
    direction: Literal["both", "up", "down"] = "both"
    unit: str = ""
    #: Relative change below which an outlier is ignored, to suppress alerts on
    #: metrics whose absolute movement is trivially small.
    min_relative_change: float = 0.05


WATCHES: tuple[Watch, ...] = (
    Watch("tps", "Transactions per second", "both", " TPS", 0.20),
    Watch("non_vote_tps", "Non-vote TPS", "both", " TPS", 0.20),
    Watch("slot_time_ms", "Slot time", "up", " ms", 0.10),
    Watch("delinquent_stake_pct", "Delinquent stake", "up", "%", 0.25),
    Watch("delinquent_count", "Delinquent validators", "up", "", 0.25),
    Watch("validator_count", "Validator count", "down", "", 0.03),
    Watch("nakamoto_coefficient", "Nakamoto coefficient", "down", "", 0.05),
    Watch("top10_stake_pct", "Top-10 stake concentration", "up", "%", 0.03),
    Watch("tvl_usd", "Solana TVL", "both", " USD", 0.05),
    Watch("price_usd", "SOL price", "both", " USD", 0.04),
    Watch("dex_volume_24h_usd", "DEX volume (24h)", "both", " USD", 0.20),
    Watch("chain_fees_24h_usd", "Chain fees (24h)", "both", " USD", 0.20),
    Watch("stablecoin_total_usd", "Stablecoin float", "both", " USD", 0.03),
    Watch("median_tx_fee_lamports", "Median transaction fee", "up", " lamports", 0.25),
    Watch("tx_failure_rate_pct", "Transaction failure rate", "up", "%", 0.15),
    Watch("gossip_node_count", "Gossip nodes", "down", "", 0.05),
    Watch("dominant_client_pct", "Dominant client share", "up", "%", 0.03),
)


def robust_z(value: float, baseline: list[float]) -> tuple[float | None, float, float]:
    """Modified z-score of ``value`` against ``baseline``.

    Returns ``(z, median, mad)``.  ``z`` is None when the MAD is zero *and* the
    value equals the median (a perfectly flat, unremarkable metric); when the
    MAD is zero but the value differs, a standard-deviation fallback is used so
    a step change on an otherwise constant metric is still caught.
    """
    if len(baseline) < 2:
        return None, (baseline[0] if baseline else value), 0.0
    median = statistics.median(baseline)
    mad = statistics.median([abs(x - median) for x in baseline])
    if mad > 0:
        return 0.6745 * (value - median) / mad, median, mad
    spread = statistics.pstdev(baseline)
    if spread > 0:
        return (value - median) / spread, median, spread
    if value == median:
        return 0.0, median, 0.0
    return (config.ROBUST_Z_CRITICAL if value != median else 0.0) * (1 if value > median else -1), median, 0.0


def _fmt(value: float | None, unit: str) -> str:
    """Human-friendly number formatting for alert text."""
    if value is None:
        return "n/a"
    if unit == " USD":
        for divisor, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
            if abs(value) >= divisor:
                return f"${value / divisor:,.2f}{suffix}"
        return f"${value:,.2f}"
    if abs(value) >= 1000:
        return f"{value:,.0f}{unit}"
    return f"{value:,.2f}{unit}"


def detect_statistical(current: dict[str, Any], history: list[dict[str, Any]]) -> tuple[list[Alert], dict[str, Any]]:
    """Detector 1: robust outliers against the rolling baseline."""
    alerts: list[Alert] = []
    scores: dict[str, Any] = {}
    for watch in WATCHES:
        value = current.get(watch.metric)
        if not isinstance(value, (int, float)):
            continue
        baseline = [
            float(r[watch.metric]) for r in history[-config.BASELINE_WINDOW:]
            if isinstance(r.get(watch.metric), (int, float))
        ]
        if len(baseline) < config.MIN_BASELINE_POINTS:
            scores[watch.metric] = {"status": "baseline_building", "points": len(baseline)}
            continue
        z, median, spread = robust_z(float(value), baseline)
        scores[watch.metric] = {
            "status": "scored", "z": round(z, 3) if z is not None else None,
            "median": median, "mad": spread, "points": len(baseline),
        }
        if z is None or abs(z) < config.ROBUST_Z_WARN:
            continue
        if watch.direction == "up" and z < 0:
            continue
        if watch.direction == "down" and z > 0:
            continue
        if median and abs(value - median) / abs(median) < watch.min_relative_change:
            continue
        severity: Severity = "critical" if abs(z) >= config.ROBUST_Z_CRITICAL else "warning"
        arrow = "above" if z > 0 else "below"
        change = ((value - median) / median * 100) if median else None
        alerts.append(Alert(
            severity=severity,
            metric=watch.metric,
            title=f"{watch.label} {'spike' if z > 0 else 'drop'}",
            detail=(
                f"{watch.label} is {_fmt(float(value), watch.unit)}, "
                f"{abs(change):.1f}% {arrow} its {len(baseline)}-run median of "
                f"{_fmt(median, watch.unit)} (robust z = {z:+.1f})."
                if change is not None else
                f"{watch.label} is {_fmt(float(value), watch.unit)} (robust z = {z:+.1f})."
            ),
            value=float(value), baseline=median, z_score=z,
            detector="robust-z", tags=["statistical"],
        ))
    return alerts, scores


def detect_rules(snapshot: dict[str, Any]) -> list[Alert]:
    """Detector 2: absolute conditions that are bad regardless of history."""
    alerts: list[Alert] = []
    m = snapshot.get("metrics", {})
    s = snapshot.get("sections", {})

    health = (s.get("cluster") or {}).get("health")
    if health and health != "ok":
        alerts.append(Alert("critical", "cluster_health", "RPC node reports unhealthy",
                            f"getHealth returned: {health}", detector="rule", tags=["network"]))

    slot_time = m.get("slot_time_ms")
    if isinstance(slot_time, (int, float)):
        if slot_time > 800:
            alerts.append(Alert("critical", "slot_time_ms", "Slot time severely degraded",
                                f"Mean slot time is {slot_time:.0f} ms against a ~400 ms target.",
                                value=slot_time, baseline=400.0, detector="rule", tags=["network"]))
        elif slot_time > 600:
            alerts.append(Alert("warning", "slot_time_ms", "Slot time above target",
                                f"Mean slot time is {slot_time:.0f} ms against a ~400 ms target.",
                                value=slot_time, baseline=400.0, detector="rule", tags=["network"]))

    delinquent = m.get("delinquent_stake_pct")
    if isinstance(delinquent, (int, float)):
        if delinquent > 5:
            alerts.append(Alert("critical", "delinquent_stake_pct", "High delinquent stake",
                                f"{delinquent:.2f}% of stake is delinquent. Consensus stalls above 33%.",
                                value=delinquent, baseline=5.0, detector="rule", tags=["validators"]))
        elif delinquent > 2:
            alerts.append(Alert("warning", "delinquent_stake_pct", "Elevated delinquent stake",
                                f"{delinquent:.2f}% of stake is delinquent (normal is below ~1%).",
                                value=delinquent, baseline=2.0, detector="rule", tags=["validators"]))

    nakamoto = m.get("nakamoto_coefficient")
    if isinstance(nakamoto, (int, float)) and nakamoto < 15:
        alerts.append(Alert("warning", "nakamoto_coefficient", "Low Nakamoto coefficient",
                            f"Only {int(nakamoto)} validators control more than one third of stake.",
                            value=float(nakamoto), baseline=15.0, detector="rule", tags=["validators"]))

    dominant = m.get("dominant_client_pct")
    if isinstance(dominant, (int, float)) and dominant > 85:
        alerts.append(Alert("warning", "dominant_client_pct", "Validator client monoculture",
                            f"{dominant:.1f}% of gossip nodes run one client implementation; "
                            "a single consensus bug would affect nearly all of them.",
                            value=dominant, baseline=85.0, detector="rule", tags=["validators"]))

    # Solana's user-transaction failure rate normally sits in the 30-50% band
    # because arbitrage bots submit speculative transactions that are expected
    # to fail. The threshold is set above that band so the rule marks genuine
    # congestion rather than normal bot behaviour; the statistical detector
    # catches smaller moves against the observed baseline.
    failure = m.get("tx_failure_rate_pct")
    if isinstance(failure, (int, float)) and failure > 65:
        alerts.append(Alert("warning", "tx_failure_rate_pct", "High transaction failure rate",
                            f"{failure:.1f}% of sampled user transactions failed on chain, above the "
                            f"30-50% band that normal arbitrage-bot activity produces.",
                            value=failure, baseline=65.0, detector="rule", tags=["network"]))

    tps = m.get("tps")
    if isinstance(tps, (int, float)) and tps < 500:
        alerts.append(Alert("critical", "tps", "Throughput collapse",
                            f"Cluster is processing {tps:.0f} TPS, far below normal operation.",
                            value=tps, baseline=500.0, detector="rule", tags=["network"]))

    status = s.get("status") or {}
    for component in status.get("degraded_components") or []:
        alerts.append(Alert("warning", "status_page", f"Statuspage: {component['name']}",
                            f"Solana's status page reports '{component['status']}' for this component.",
                            detector="rule", tags=["status"]))

    for asset in (s.get("stablecoins") or {}).get("depegged") or []:
        alerts.append(Alert("warning", "stablecoin_peg", f"{asset['symbol']} off peg",
                            f"{asset['name']} is quoted at ${asset['price']:.4f} with "
                            f"{_fmt(asset['circulating_usd'], ' USD')} circulating on Solana.",
                            detector="rule", tags=["economy"]))
    return alerts


def detect_correlations(snapshot: dict[str, Any], history: list[dict[str, Any]]) -> list[Alert]:
    """Detector 3: signals visible only when several sources are held together."""
    alerts: list[Alert] = []
    m = snapshot.get("metrics", {})

    price_change = m.get("change_24h_pct")
    tvl_change = (snapshot.get("sections", {}).get("tvl") or {}).get("change_1d_pct")
    if isinstance(price_change, (int, float)) and isinstance(tvl_change, (int, float)):
        gap = tvl_change - price_change
        if abs(price_change) > 5 and abs(gap) > 8:
            direction = "held up against" if gap > 0 else "fell faster than"
            alerts.append(Alert(
                "info", "tvl_price_divergence", "TVL and price are diverging",
                f"SOL moved {price_change:+.1f}% over 24h while Solana TVL moved {tvl_change:+.1f}% - "
                f"capital {direction} the token. A {gap:+.1f} point gap usually means the move is "
                "driven by traders rather than by users entering or leaving protocols.",
                value=gap, detector="correlation", tags=["economy", "cross-source"],
            ))

    dex = m.get("dex_volume_24h_usd")
    fees = m.get("chain_fees_24h_usd")
    if isinstance(dex, (int, float)) and isinstance(fees, (int, float)) and dex > 0:
        ratio = fees / dex * 10_000  # basis points of volume paid as chain fees
        baseline = [
            float(r["chain_fees_24h_usd"]) / float(r["dex_volume_24h_usd"]) * 10_000
            for r in history[-config.BASELINE_WINDOW:]
            if r.get("dex_volume_24h_usd") and r.get("chain_fees_24h_usd")
        ]
        if len(baseline) >= config.MIN_BASELINE_POINTS:
            z, median, _ = robust_z(ratio, baseline)
            if z is not None and abs(z) >= config.ROBUST_Z_WARN and median:
                alerts.append(Alert(
                    "info", "fee_to_volume_ratio", "Fee-to-volume ratio has shifted",
                    f"Solana is collecting {ratio:.2f} bps of DEX volume in chain fees against a "
                    f"baseline of {median:.2f} bps (robust z = {z:+.1f}). A rise points at congestion "
                    "pricing; a fall points at volume arriving through cheaper paths.",
                    value=ratio, baseline=median, z_score=z,
                    detector="correlation", tags=["economy", "cross-source"],
                ))

    tps = m.get("tps")
    failure = m.get("tx_failure_rate_pct")
    if isinstance(tps, (int, float)) and isinstance(failure, (int, float)):
        tps_base = [float(r["tps"]) for r in history[-config.BASELINE_WINDOW:] if r.get("tps")]
        fail_base = [float(r["tx_failure_rate_pct"]) for r in history[-config.BASELINE_WINDOW:]
                     if r.get("tx_failure_rate_pct")]
        if len(tps_base) >= config.MIN_BASELINE_POINTS and len(fail_base) >= config.MIN_BASELINE_POINTS:
            z_tps, med_tps, _ = robust_z(float(tps), tps_base)
            z_fail, med_fail, _ = robust_z(float(failure), fail_base)
            if z_tps is not None and z_fail is not None and z_tps > 2 and z_fail > 2:
                alerts.append(Alert(
                    "warning", "congestion_signature", "Congestion signature detected",
                    f"Throughput ({tps:.0f} TPS vs {med_tps:.0f} baseline) and the on-chain failure "
                    f"rate ({failure:.1f}% vs {med_fail:.1f}%) are both elevated. Rising volume that "
                    "arrives with rising failures is demand the cluster is not fully absorbing.",
                    value=float(failure), baseline=med_fail, z_score=z_fail,
                    detector="correlation", tags=["network", "cross-source"],
                ))

    stables = m.get("stablecoin_total_usd")
    tvl = m.get("tvl_usd")
    if isinstance(stables, (int, float)) and isinstance(tvl, (int, float)) and tvl > 0:
        ratio = stables / tvl * 100
        base = [
            float(r["stablecoin_total_usd"]) / float(r["tvl_usd"]) * 100
            for r in history[-config.BASELINE_WINDOW:]
            if r.get("stablecoin_total_usd") and r.get("tvl_usd")
        ]
        if len(base) >= config.MIN_BASELINE_POINTS:
            z, median, _ = robust_z(ratio, base)
            if z is not None and abs(z) >= config.ROBUST_Z_WARN:
                alerts.append(Alert(
                    "info", "stablecoin_tvl_ratio", "Stablecoin share of TVL has shifted",
                    f"Stablecoin float is {ratio:.1f}% of chain TVL against a {median:.1f}% baseline "
                    f"(robust z = {z:+.1f}). A rising share is dry powder sitting on the sidelines; "
                    "a falling share is capital rotating into risk.",
                    value=ratio, baseline=median, z_score=z,
                    detector="correlation", tags=["economy", "cross-source"],
                ))
    return alerts


def run_detection(snapshot: dict[str, Any], history: list[dict[str, Any]]) -> dict[str, Any]:
    """Run all three detectors and return alerts plus detector diagnostics."""
    metrics = snapshot.get("metrics", {})
    statistical, scores = detect_statistical(metrics, history)
    alerts = statistical + detect_rules(snapshot) + detect_correlations(snapshot, history)
    alerts.sort(key=lambda a: (SEVERITY_ORDER[a.severity], a.metric))

    scored = sum(1 for v in scores.values() if v.get("status") == "scored")
    return {
        "alerts": [a.to_dict() for a in alerts],
        "counts": {
            "critical": sum(1 for a in alerts if a.severity == "critical"),
            "warning": sum(1 for a in alerts if a.severity == "warning"),
            "info": sum(1 for a in alerts if a.severity == "info"),
            "total": len(alerts),
        },
        "baseline_runs": len(history),
        "metrics_scored": scored,
        "metrics_building_baseline": len(scores) - scored,
        "baseline_ready": len(history) >= config.MIN_BASELINE_POINTS,
        "scores": scores,
        "method": {
            "statistical": "modified z-score 0.6745*(x-median)/MAD over a rolling window",
            "window_runs": config.BASELINE_WINDOW,
            "warn_z": config.ROBUST_Z_WARN,
            "critical_z": config.ROBUST_Z_CRITICAL,
            "min_points": config.MIN_BASELINE_POINTS,
        },
    }
