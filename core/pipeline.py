"""Run every collector, assemble the snapshot, detect anomalies.

The pipeline is deliberately the only place that knows about all the sources at
once.  Collectors stay independent and ignorant of each other; renderers stay
ignorant of the network.

Collectors are grouped so the concurrency respects the upstream rate limits:

* the Solana RPC group runs sequentially on one client, so a run costs one
  provider's budget and failover stays predictable;
* the CoinGecko group runs sequentially, because its anonymous tier throttles
  aggressively;
* everything else runs in parallel on a small thread pool.
"""

from __future__ import annotations

import platform
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

from analysis import anomaly, history as history_store
from collectors import blocks as block_collector, defi, market, news, rpc
from core import config
from core.net import SourceResult, iso, utc_now


def _rpc_group(client: rpc.RpcClient, *, sample_blocks: bool) -> dict[str, SourceResult]:
    """Sequential Solana RPC calls against a single failover client."""
    results = {
        "cluster": rpc.collect_cluster(client),
        "performance": rpc.collect_performance(client),
        "validators": rpc.collect_validators(client),
        "cluster_nodes": rpc.collect_cluster_nodes(client),
        "supply": rpc.collect_supply(client),
        "accounts": rpc.collect_watched_accounts(client),
    }
    if sample_blocks:
        results["blocks"] = block_collector.collect_block_sample(client)
    return results


def _coingecko_group() -> dict[str, SourceResult]:
    """Sequential CoinGecko calls; the anonymous tier will not take a burst."""
    return {
        "market": market.collect_sol_market(),
        "price_history": market.collect_price_history(),
        "ecosystem_tokens": market.collect_ecosystem_tokens(),
    }


def _data(result: SourceResult | None, default: Any = None) -> Any:
    """Payload of a successful result, else ``default``."""
    return result.data if result and result.ok else default


def collect_all(*, sample_blocks: bool = True, workers: int = 6) -> dict[str, SourceResult]:
    """Execute every collector and return them keyed by section name."""
    client = rpc.RpcClient()
    tasks: dict[str, Callable[[], SourceResult]] = {
        "tvl": defi.collect_chain_tvl,
        "protocols": defi.collect_protocols,
        "dex": defi.collect_dex_volume,
        "fees": defi.collect_fees,
        "stablecoins": defi.collect_stablecoins,
        "news": news.collect_news,
        "simds": news.collect_simds,
        "accepted_simds": news.collect_accepted_simds,
        "releases": news.collect_client_releases,
        "status": news.collect_status,
    }
    results: dict[str, SourceResult] = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        rpc_future = pool.submit(_rpc_group, client, sample_blocks=sample_blocks)
        gecko_future = pool.submit(_coingecko_group)
        futures = {key: pool.submit(fn) for key, fn in tasks.items()}
        for key, future in futures.items():
            results[key] = future.result()
        results.update(rpc_future.result())
        results.update(gecko_future.result())
    results["_rpc_client"] = SourceResult(  # bookkeeping, not a data source
        name="_rpc_client", url=client.active, ok=True,
        data={"endpoint": client.active, "calls": client.calls, "failures": client.failures},
    )
    return results


def derive_metrics(results: dict[str, SourceResult]) -> dict[str, Any]:
    """Flatten the collected sections into the scalar metric bag.

    This is the vocabulary shared by history, anomaly detection and every
    renderer, so each metric is computed exactly once and in one place.
    """
    cluster = _data(results.get("cluster"), {}) or {}
    perf = _data(results.get("performance"), {}) or {}
    validators = _data(results.get("validators"), {}) or {}
    nodes = _data(results.get("cluster_nodes"), {}) or {}
    supply = _data(results.get("supply"), {}) or {}
    sample = _data(results.get("blocks"), {}) or {}
    market_data = _data(results.get("market"), {}) or {}
    tvl = _data(results.get("tvl"), {}) or {}
    protocols = _data(results.get("protocols"), {}) or {}
    dex = _data(results.get("dex"), {}) or {}
    fees = _data(results.get("fees"), {}) or {}
    stables = _data(results.get("stablecoins"), {}) or {}

    metrics: dict[str, Any] = {
        "tps": perf.get("tps_current"),
        "tps_mean": perf.get("tps_mean"),
        "non_vote_tps": perf.get("non_vote_tps_current"),
        "slot_time_ms": perf.get("slot_time_ms_current"),
        "vote_tx_share_pct": sample.get("vote_tx_share_pct") or perf.get("vote_share_pct"),
        "epoch": cluster.get("epoch"),
        "epoch_progress_pct": cluster.get("epoch_progress_pct"),
        "block_height": cluster.get("block_height"),
        "transaction_count": cluster.get("transaction_count"),
        "validator_count": validators.get("validator_count"),
        "active_validator_count": validators.get("active_count"),
        "delinquent_count": validators.get("delinquent_count"),
        "delinquent_stake_pct": validators.get("delinquent_stake_pct"),
        "nakamoto_coefficient": validators.get("nakamoto_coefficient"),
        "top10_stake_pct": validators.get("top10_stake_pct"),
        "total_stake_sol": validators.get("total_stake_sol"),
        "gossip_node_count": nodes.get("gossip_node_count"),
        "dominant_client_pct": nodes.get("dominant_client_pct"),
        "distinct_client_count": len(nodes.get("clients") or []) or None,
        "total_supply_sol": supply.get("total_supply_sol"),
        "circulating_supply_sol": supply.get("circulating_supply_sol"),
        "inflation_total_pct": supply.get("inflation_total_pct"),
        "median_tx_fee_lamports": sample.get("median_tx_fee_lamports"),
        "median_priority_fee_lamports": sample.get("median_priority_fee_lamports"),
        "tx_failure_rate_pct": sample.get("tx_failure_rate_pct"),
        "priority_fee_share_pct": sample.get("priority_fee_share_pct"),
        "avg_unique_payers_per_block": sample.get("avg_unique_payers_per_block"),
        "unique_payers_in_sample": sample.get("unique_payers_in_sample"),
        "price_usd": market_data.get("price_usd"),
        "market_cap_usd": market_data.get("market_cap_usd"),
        "volume_24h_usd": market_data.get("volume_24h_usd"),
        "change_24h_pct": market_data.get("change_24h_pct"),
        "tvl_usd": tvl.get("tvl_usd"),
        "defi_tvl_usd": protocols.get("defi_tvl_usd"),
        "rwa_tvl_usd": protocols.get("rwa_tvl_usd"),
        "tokenized_equity_tvl_usd": protocols.get("tokenized_equity_tvl_usd"),
        "dex_volume_24h_usd": dex.get("total_24h_usd"),
        "chain_fees_24h_usd": fees.get("total_24h_usd"),
        "stablecoin_total_usd": stables.get("total_usd"),
    }

    # Derived cross-source ratios: cheap to compute, and each one says something
    # no single source states directly.
    price = metrics.get("price_usd")
    circulating = metrics.get("circulating_supply_sol")
    if price and circulating:
        metrics["onchain_market_cap_usd"] = price * circulating
    if metrics.get("total_stake_sol") and metrics.get("circulating_supply_sol"):
        metrics["staking_ratio_pct"] = (
            metrics["total_stake_sol"] / metrics["circulating_supply_sol"] * 100
        )
    if metrics.get("total_stake_sol") and price:
        metrics["staked_value_usd"] = metrics["total_stake_sol"] * price
    if metrics.get("tvl_usd") and metrics.get("market_cap_usd"):
        metrics["mcap_to_tvl"] = metrics["market_cap_usd"] / metrics["tvl_usd"]
    if metrics.get("stablecoin_total_usd") and metrics.get("tvl_usd"):
        metrics["stablecoin_share_of_tvl_pct"] = (
            metrics["stablecoin_total_usd"] / metrics["tvl_usd"] * 100
        )
    if metrics.get("chain_fees_24h_usd") and metrics.get("dex_volume_24h_usd"):
        metrics["fee_per_dex_volume_bps"] = (
            metrics["chain_fees_24h_usd"] / metrics["dex_volume_24h_usd"] * 10_000
        )
    if metrics.get("median_tx_fee_lamports") and price:
        metrics["median_tx_fee_usd"] = (
            metrics["median_tx_fee_lamports"] / config.LAMPORTS_PER_SOL * price
        )
    if metrics.get("chain_fees_24h_usd") and metrics.get("market_cap_usd"):
        metrics["annualised_fee_to_mcap_pct"] = (
            metrics["chain_fees_24h_usd"] * 365 / metrics["market_cap_usd"] * 100
        )
    if metrics.get("non_vote_tps"):
        metrics["projected_daily_user_txs"] = metrics["non_vote_tps"] * 86_400

    ok = [k for k, r in results.items() if not k.startswith("_") and r.ok]
    failed = [k for k, r in results.items() if not k.startswith("_") and not r.ok]
    metrics["sources_ok"] = len(ok)
    metrics["sources_failed"] = len(failed)
    return metrics


def build_snapshot(results: dict[str, SourceResult], *, started: float) -> dict[str, Any]:
    """Assemble the full snapshot: sections, metrics, source ledger, alerts."""
    generated_at = iso(utc_now())
    sections = {
        key: result.data for key, result in results.items()
        if not key.startswith("_") and result.ok
    }
    metrics = derive_metrics(results)

    past = history_store.load_history()
    detection = anomaly.run_detection({"metrics": metrics, "sections": sections}, past)
    record = history_store.build_record(generated_at, metrics)
    total_records = history_store.append_record(record)
    trend_history = past + [record]

    sources = [r.to_dict() for k, r in results.items() if not k.startswith("_")]
    sources.sort(key=lambda s: (s["ok"], s["name"]))
    client_info = _data(results.get("_rpc_client"), {}) or {}

    return {
        "schema_version": "1.0",
        "generated_at": generated_at,
        "runtime_seconds": round(time.time() - started, 2),
        "generator": {
            "name": "Solana Pulse",
            "version": "1.0.0",
            "python": platform.python_version(),
            "implementation": sys.implementation.name,
            "dependencies": "Python standard library only",
            "rpc_endpoint": client_info.get("endpoint"),
            "rpc_calls": client_info.get("calls"),
        },
        "metrics": metrics,
        "sections": sections,
        "alerts": detection["alerts"],
        "anomaly_detection": {k: v for k, v in detection.items() if k != "alerts"},
        "sources": sources,
        "source_summary": {
            "total": len(sources),
            "ok": sum(1 for s in sources if s["ok"]),
            "degraded": [s["name"] for s in sources if not s["ok"]],
        },
        "history": {
            "records": total_records,
            "path": config.HISTORY_PATH,
            "first_run": trend_history[0]["ts"] if trend_history else generated_at,
        },
        "_trend_history": trend_history,
    }


def run(*, sample_blocks: bool = True) -> dict[str, Any]:
    """Collect everything and return a finished snapshot."""
    started = time.time()
    results = collect_all(sample_blocks=sample_blocks)
    return build_snapshot(results, started=started)
