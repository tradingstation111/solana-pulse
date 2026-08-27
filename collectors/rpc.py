"""Solana JSON-RPC collectors.

All calls go to public, keyless mainnet endpoints with automatic failover.
Each public function returns a :class:`~core.net.SourceResult`, so a dead
endpoint costs one dashboard section rather than the whole run.
"""

from __future__ import annotations

import statistics
from typing import Any

from core import config
from core.net import FetchError, SourceResult, guarded, rpc_post


class RpcClient:
    """Thin JSON-RPC client that fails over across the configured endpoints.

    The endpoint that answered last is remembered and tried first, so a single
    run normally hits one provider and stays inside its anonymous rate budget.
    """

    def __init__(self, endpoints: tuple[str, ...] = config.RPC_ENDPOINTS) -> None:
        self.endpoints = list(endpoints)
        self.active = self.endpoints[0]
        self.failures: dict[str, str] = {}
        self.calls = 0

    def call(self, method: str, params: list[Any] | None = None, *, timeout: float = 30.0) -> Any:
        """Invoke ``method``, walking the endpoint list until one succeeds."""
        order = [self.active] + [e for e in self.endpoints if e != self.active]
        last: Exception | None = None
        for endpoint in order:
            try:
                result = rpc_post(endpoint, method, params, timeout=timeout)
                self.active = endpoint
                self.calls += 1
                return result
            except Exception as exc:  # noqa: BLE001 - try the next provider
                last = exc
                self.failures[f"{endpoint} {method}"] = str(exc)[:200]
        raise FetchError(f"all RPC endpoints failed for {method}: {last}")


def collect_cluster(client: RpcClient) -> SourceResult:
    """Health, version, epoch position, block height and current slot."""

    def run() -> dict[str, Any]:
        health = "unknown"
        try:
            health = client.call("getHealth")
        except Exception as exc:  # noqa: BLE001 - an unhealthy node answers with an error
            health = f"unhealthy: {str(exc)[:120]}"
        epoch = client.call("getEpochInfo")
        version = client.call("getVersion")
        slot = epoch.get("absoluteSlot")
        block_time = client.call("getBlockTime", [slot - 32]) if slot else None
        slots_in_epoch = epoch.get("slotsInEpoch") or 0
        slot_index = epoch.get("slotIndex") or 0
        progress = (slot_index / slots_in_epoch * 100) if slots_in_epoch else None
        return {
            "health": health,
            "endpoint": client.active,
            "solana_core": version.get("solana-core"),
            "feature_set": version.get("feature-set"),
            "epoch": epoch.get("epoch"),
            "absolute_slot": slot,
            "block_height": epoch.get("blockHeight"),
            "slot_index": slot_index,
            "slots_in_epoch": slots_in_epoch,
            "epoch_progress_pct": progress,
            "epoch_slots_remaining": max(slots_in_epoch - slot_index, 0),
            "transaction_count": epoch.get("transactionCount"),
            "recent_block_time": block_time,
        }

    return guarded("Solana RPC: cluster", client.active, run)


def collect_performance(client: RpcClient) -> SourceResult:
    """Recent performance samples -> TPS, non-vote TPS and mean slot time."""

    def run() -> dict[str, Any]:
        samples = client.call("getRecentPerformanceSamples", [30]) or []
        series = []
        for s in samples:
            period = s.get("samplePeriodSecs") or 0
            slots = s.get("numSlots") or 0
            if not period or not slots:
                continue
            total = s.get("numTransactions") or 0
            non_vote = s.get("numNonVoteTransactions")
            series.append({
                "slot": s.get("slot"),
                "tps": total / period,
                "non_vote_tps": (non_vote / period) if non_vote is not None else None,
                "slot_time_ms": period / slots * 1000,
                "vote_share_pct": ((total - non_vote) / total * 100) if non_vote is not None and total else None,
            })
        if not series:
            raise FetchError("getRecentPerformanceSamples returned no usable samples")
        series.reverse()  # oldest first, so charts read left to right
        latest = series[-1]
        tps_values = [x["tps"] for x in series]
        nv = [x["non_vote_tps"] for x in series if x["non_vote_tps"] is not None]
        slot_ms = [x["slot_time_ms"] for x in series]
        return {
            "samples": series,
            "tps_current": latest["tps"],
            "tps_mean": statistics.fmean(tps_values),
            "tps_max": max(tps_values),
            "tps_min": min(tps_values),
            "non_vote_tps_current": latest["non_vote_tps"],
            "non_vote_tps_mean": statistics.fmean(nv) if nv else None,
            "slot_time_ms_current": latest["slot_time_ms"],
            "slot_time_ms_mean": statistics.fmean(slot_ms),
            "vote_share_pct": latest["vote_share_pct"],
            "window_minutes": len(series),
        }

    return guarded("Solana RPC: performance samples", client.active, run)


def _nakamoto(sorted_stakes: list[int], total: float) -> int:
    """Smallest number of validators whose combined stake exceeds 33.3%.

    That is the superminority: the group that could halt consensus by going
    offline together.  Higher is more decentralised.
    """
    running = 0.0
    for index, stake in enumerate(sorted_stakes, start=1):
        running += stake
        if running / total > 1 / 3:
            return index
    return len(sorted_stakes)


def collect_validators(client: RpcClient) -> SourceResult:
    """Vote accounts -> counts, stake concentration, commissions, delinquency."""

    def run() -> dict[str, Any]:
        accounts = client.call("getVoteAccounts")
        current = accounts.get("current") or []
        delinquent = accounts.get("delinquent") or []
        lam = config.LAMPORTS_PER_SOL

        def norm(entry: dict[str, Any], is_delinquent: bool) -> dict[str, Any]:
            credits = entry.get("epochCredits") or []
            earned = (credits[-1][1] - credits[-1][2]) if credits else None
            return {
                "vote_pubkey": entry.get("votePubkey"),
                "node_pubkey": entry.get("nodePubkey"),
                "stake_sol": (entry.get("activatedStake") or 0) / lam,
                "commission": entry.get("commission"),
                "last_vote": entry.get("lastVote"),
                "root_slot": entry.get("rootSlot"),
                "delinquent": is_delinquent,
                "epoch_credits": earned,
            }

        rows = [norm(v, False) for v in current] + [norm(v, True) for v in delinquent]
        rows.sort(key=lambda r: -r["stake_sol"])
        total_stake = sum(r["stake_sol"] for r in rows)
        active_stake = sum(r["stake_sol"] for r in rows if not r["delinquent"])
        delinquent_stake = total_stake - active_stake
        stakes = [int(r["stake_sol"]) for r in rows if r["stake_sol"] > 0]

        for rank, row in enumerate(rows, start=1):
            row["rank"] = rank
            row["stake_pct"] = (row["stake_sol"] / total_stake * 100) if total_stake else 0.0

        commissions = [r["commission"] for r in rows if r["commission"] is not None]
        buckets: dict[str, int] = {"0%": 0, "1-5%": 0, "6-10%": 0, "11-50%": 0, "51-100%": 0}
        for c in commissions:
            if c == 0:
                buckets["0%"] += 1
            elif c <= 5:
                buckets["1-5%"] += 1
            elif c <= 10:
                buckets["6-10%"] += 1
            elif c <= 50:
                buckets["11-50%"] += 1
            else:
                buckets["51-100%"] += 1

        def top_share(n: int) -> float:
            return sum(r["stake_sol"] for r in rows[:n]) / total_stake * 100 if total_stake else 0.0

        return {
            "validator_count": len(rows),
            "active_count": len(current),
            "delinquent_count": len(delinquent),
            "total_stake_sol": total_stake,
            "active_stake_sol": active_stake,
            "delinquent_stake_sol": delinquent_stake,
            "delinquent_stake_pct": (delinquent_stake / total_stake * 100) if total_stake else 0.0,
            "nakamoto_coefficient": _nakamoto(stakes, float(sum(stakes))) if stakes else None,
            "top1_stake_pct": top_share(1),
            "top10_stake_pct": top_share(10),
            "top20_stake_pct": top_share(20),
            "top100_stake_pct": top_share(100),
            "median_stake_sol": statistics.median([r["stake_sol"] for r in rows]) if rows else 0.0,
            "median_commission": statistics.median(commissions) if commissions else None,
            "zero_commission_count": buckets["0%"],
            "commission_buckets": buckets,
            "validators": rows,
            "top_delinquent": [r for r in rows if r["delinquent"]][:15],
        }

    return guarded("Solana RPC: vote accounts", client.active, run)


def collect_cluster_nodes(client: RpcClient) -> SourceResult:
    """Gossip view -> validator client mix (Agave / Frankendancer / Jito / ...).

    Client diversity is the headline resilience metric for Solana right now:
    a monoculture means one consensus bug can stop the chain.
    """

    def run() -> dict[str, Any]:
        nodes = client.call("getClusterNodes") or []
        clients: dict[str, int] = {}
        versions: dict[str, int] = {}
        rpc_exposed = 0
        for node in nodes:
            name = node.get("clientId") or "unknown"
            clients[name] = clients.get(name, 0) + 1
            ver = node.get("version") or "unknown"
            versions[ver] = versions.get(ver, 0) + 1
            if node.get("rpc"):
                rpc_exposed += 1
        total = len(nodes) or 1
        client_rows = [
            {"client": k, "nodes": v, "share_pct": v / total * 100}
            for k, v in sorted(clients.items(), key=lambda kv: -kv[1])
        ]
        version_rows = [
            {"version": k, "nodes": v, "share_pct": v / total * 100}
            for k, v in sorted(versions.items(), key=lambda kv: -kv[1])[:12]
        ]
        return {
            "gossip_node_count": len(nodes),
            "rpc_exposed_count": rpc_exposed,
            "clients": client_rows,
            "versions": version_rows,
            "distinct_versions": len(versions),
            "dominant_client_pct": client_rows[0]["share_pct"] if client_rows else None,
            "dominant_client": client_rows[0]["client"] if client_rows else None,
        }

    return guarded("Solana RPC: cluster nodes", client.active, run)


def collect_supply(client: RpcClient) -> SourceResult:
    """Total / circulating SOL supply and the current inflation schedule."""

    def run() -> dict[str, Any]:
        supply = client.call("getSupply", [{"excludeNonCirculatingAccountsList": True}], timeout=45.0)
        value = supply.get("value", supply)
        lam = config.LAMPORTS_PER_SOL
        total = (value.get("total") or 0) / lam
        circulating = (value.get("circulating") or 0) / lam
        inflation = {}
        try:
            inflation = client.call("getInflationRate") or {}
        except Exception:  # noqa: BLE001 - optional enrichment
            inflation = {}
        return {
            "total_supply_sol": total,
            "circulating_supply_sol": circulating,
            "non_circulating_sol": (value.get("nonCirculating") or 0) / lam,
            "circulating_pct": (circulating / total * 100) if total else None,
            "inflation_total_pct": (inflation.get("total") or 0) * 100 or None,
            "inflation_validator_pct": (inflation.get("validator") or 0) * 100 or None,
            "inflation_epoch": inflation.get("epoch"),
        }

    return guarded("Solana RPC: supply & inflation", client.active, run)


def collect_watched_accounts(client: RpcClient) -> SourceResult:
    """Balances and recent signature activity for a few labelled mainnet accounts."""

    def run() -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for account in config.WATCHED_ACCOUNTS:
            row = dict(account)
            try:
                balance = client.call("getBalance", [account["address"]])
                row["balance_sol"] = (balance.get("value") or 0) / config.LAMPORTS_PER_SOL
            except Exception as exc:  # noqa: BLE001 - per-account degradation
                row["balance_sol"] = None
                row["error"] = str(exc)[:120]
            try:
                sigs = client.call("getSignaturesForAddress", [account["address"], {"limit": 25}]) or []
                times = [s["blockTime"] for s in sigs if s.get("blockTime")]
                failed = sum(1 for s in sigs if s.get("err"))
                row["recent_signatures"] = len(sigs)
                row["failed_in_sample"] = failed
                row["failure_rate_pct"] = (failed / len(sigs) * 100) if sigs else None
                row["last_activity_unix"] = max(times) if times else None
                # Signature timestamps span a window; 25 sigs over N seconds is a
                # crude but honest per-account throughput reading.
                if len(times) > 1 and (max(times) - min(times)) > 0:
                    row["sig_rate_per_min"] = len(times) / ((max(times) - min(times)) / 60)
                else:
                    row["sig_rate_per_min"] = None
            except Exception as exc:  # noqa: BLE001
                row["recent_signatures"] = None
                row["error"] = str(exc)[:120]
            rows.append(row)
        return rows

    return guarded("Solana RPC: watched accounts", client.active, run)
