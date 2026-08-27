"""On-chain block sampling.

Aggregate APIs will tell you Solana's TPS.  None of them will tell you what the
median transaction on Solana actually *cost* right now, how many of them
failed, or how many distinct wallets paid for them - not without an API key.

This module derives those directly from raw blocks pulled over public RPC:

* median / p90 transaction fee, split into base fee and priority fee;
* transaction success rate and vote-vs-user transaction mix;
* unique fee payers, with a capture-recapture estimate of the active-wallet
  population in the sampling window (see :func:`_chapman_estimate`).

Each sampled block is roughly 6 MiB, so :data:`core.config.BLOCK_SAMPLE_COUNT`
is the knob that trades detail for bandwidth.
"""

from __future__ import annotations

import statistics
from typing import Any

from core import config
from core.net import FetchError, SourceResult, guarded
from collectors.rpc import RpcClient

BASE_FEE_LAMPORTS_PER_SIGNATURE = 5_000


def _chapman_estimate(n1: int, n2: int, overlap: int) -> float | None:
    """Chapman's bias-corrected Lincoln-Petersen population estimate.

    Two independent "captures" of wallets (two disjoint halves of the sampled
    blocks) of size ``n1`` and ``n2`` share ``overlap`` members.  If wallets
    were equally likely to appear in either capture, the population is about
    ``(n1+1)(n2+1)/(overlap+1) - 1``.

    Real wallet activity is not equally likely - bots appear in every block,
    humans in one - so this over-weights heavy users and the result is best
    read as an order-of-magnitude figure for the sampling window only.  It is
    labelled as such everywhere it is displayed.
    """
    if overlap <= 0 or n1 <= 0 or n2 <= 0:
        return None
    return ((n1 + 1) * (n2 + 1) / (overlap + 1)) - 1


def _fetch_block(client: RpcClient, slot: int, max_backtrack: int = 8) -> dict[str, Any] | None:
    """Fetch the first confirmed block at or below ``slot``.

    Solana skips slots when a leader misses its turn, so a requested slot may
    hold no block; we walk backwards a few slots before giving up.
    """
    for offset in range(max_backtrack):
        try:
            return client.call(
                "getBlock",
                [slot - offset, {
                    "encoding": "json",
                    "transactionDetails": "accounts",
                    "rewards": False,
                    "maxSupportedTransactionVersion": 0,
                }],
                timeout=60.0,
            )
        except Exception as exc:  # noqa: BLE001 - skipped slot or transient RPC error
            if "skipped" in str(exc).lower() or "-3200" in str(exc):
                continue
            if offset >= 2:
                return None
    return None


def summarise_block(block: dict[str, Any]) -> dict[str, Any]:
    """Reduce one raw block to the statistics the report needs.

    Pure function over an RPC payload - unit-tested against a fixture with no
    network access.
    """
    txs = block.get("transactions") or []
    fees: list[int] = []
    priority_fees: list[int] = []
    payers: set[str] = set()
    vote_txs = 0
    failed_user = 0
    failed_all = 0
    total_fee_lamports = 0

    for tx in txs:
        meta = tx.get("meta") or {}
        inner = tx.get("transaction") or {}
        keys = inner.get("accountKeys") or []
        if not keys:
            continue
        payer = keys[0].get("pubkey") if isinstance(keys[0], dict) else keys[0]
        is_vote = any(
            (k.get("pubkey") if isinstance(k, dict) else k) == config.VOTE_PROGRAM_ID
            for k in keys
        )
        fee = meta.get("fee") or 0
        total_fee_lamports += fee
        errored = bool(meta.get("err"))
        if errored:
            failed_all += 1
        if is_vote:
            vote_txs += 1
            continue  # vote fees are a consensus cost, not a user-facing price
        if errored:
            failed_user += 1
        if payer:
            payers.add(payer)
        signers = sum(1 for k in keys if isinstance(k, dict) and k.get("signer")) or 1
        base = signers * BASE_FEE_LAMPORTS_PER_SIGNATURE
        fees.append(fee)
        priority_fees.append(max(fee - base, 0))

    user_txs = len(txs) - vote_txs
    return {
        "slot": block.get("parentSlot", 0) + 1,
        "block_time": block.get("blockTime"),
        "block_height": block.get("blockHeight"),
        "tx_count": len(txs),
        "vote_tx_count": vote_txs,
        "user_tx_count": user_txs,
        "failed_tx_count": failed_all,
        "failed_user_tx_count": failed_user,
        # Reported over user transactions only. Vote transactions almost never
        # fail, so including them in the denominator would understate the rate
        # a wallet actually experiences.
        "failure_rate_pct": (failed_user / user_txs * 100) if user_txs else None,
        "unique_fee_payers": len(payers),
        "payers": payers,
        "total_fee_lamports": total_fee_lamports,
        "median_user_fee_lamports": statistics.median(fees) if fees else None,
        "mean_user_fee_lamports": statistics.fmean(fees) if fees else None,
        "p90_user_fee_lamports": (
            statistics.quantiles(fees, n=10)[8] if len(fees) >= 10 else (max(fees) if fees else None)
        ),
        "median_priority_fee_lamports": statistics.median(priority_fees) if priority_fees else None,
        "priority_fee_share_pct": (
            sum(priority_fees) / sum(fees) * 100 if fees and sum(fees) else None
        ),
    }


def collect_block_sample(client: RpcClient) -> SourceResult:
    """Sample recent blocks and derive fee, reliability and wallet statistics."""

    def run() -> dict[str, Any]:
        tip = client.call("getSlot", [{"commitment": "finalized"}])
        if not isinstance(tip, int):
            raise FetchError("getSlot did not return a slot number")
        summaries: list[dict[str, Any]] = []
        for i in range(config.BLOCK_SAMPLE_COUNT):
            # Start 40 slots behind the tip so the block is comfortably finalised.
            target = tip - 40 - i * config.BLOCK_SAMPLE_SPACING
            block = _fetch_block(client, target)
            if block:
                summaries.append(summarise_block(block))
        if not summaries:
            raise FetchError("no blocks could be fetched from any endpoint")

        summaries.sort(key=lambda b: b["block_time"] or 0)
        lam = config.LAMPORTS_PER_SOL

        # Capture-recapture over two disjoint halves of the sample.
        half = len(summaries) // 2
        first = set().union(*[b["payers"] for b in summaries[:half]]) if half else set()
        second = set().union(*[b["payers"] for b in summaries[half:]]) if half else set()
        overlap = len(first & second)
        window_estimate = _chapman_estimate(len(first), len(second), overlap)

        union: set[str] = set().union(*[b["payers"] for b in summaries])
        seen: set[str] = set()
        first_sightings = 0
        for block in summaries:
            first_sightings += len(block["payers"] - seen)
            seen |= block["payers"]
        times = [b["block_time"] for b in summaries if b["block_time"]]
        span_s = (max(times) - min(times)) if len(times) > 1 else 0

        medians = [b["median_user_fee_lamports"] for b in summaries if b["median_user_fee_lamports"]]
        p90s = [b["p90_user_fee_lamports"] for b in summaries if b["p90_user_fee_lamports"]]
        prio = [b["median_priority_fee_lamports"] for b in summaries if b["median_priority_fee_lamports"] is not None]
        fail = [b["failure_rate_pct"] for b in summaries if b["failure_rate_pct"] is not None]
        prio_share = [b["priority_fee_share_pct"] for b in summaries if b["priority_fee_share_pct"] is not None]

        total_txs = sum(b["tx_count"] for b in summaries)
        total_votes = sum(b["vote_tx_count"] for b in summaries)
        total_fees_sol = sum(b["total_fee_lamports"] for b in summaries) / lam
        blocks = len(summaries)

        for block in summaries:
            block.pop("payers", None)  # sets are not JSON-serialisable and not needed downstream

        return {
            "blocks_sampled": blocks,
            "slot_tip": tip,
            "sample_span_seconds": span_s,
            "median_tx_fee_lamports": statistics.median(medians) if medians else None,
            "median_tx_fee_sol": (statistics.median(medians) / lam) if medians else None,
            "p90_tx_fee_lamports": statistics.median(p90s) if p90s else None,
            "median_priority_fee_lamports": statistics.median(prio) if prio else None,
            "priority_fee_share_pct": statistics.fmean(prio_share) if prio_share else None,
            "tx_failure_rate_pct": statistics.fmean(fail) if fail else None,
            "vote_tx_share_pct": (total_votes / total_txs * 100) if total_txs else None,
            "avg_txs_per_block": total_txs / blocks,
            "avg_user_txs_per_block": sum(b["user_tx_count"] for b in summaries) / blocks,
            "avg_unique_payers_per_block": sum(b["unique_fee_payers"] for b in summaries) / blocks,
            "unique_payers_in_sample": len(union),
            "payer_recapture_overlap": overlap,
            "window_active_wallet_estimate": window_estimate,
            "new_payer_discovery_rate_per_s": (first_sightings / span_s) if span_s else None,
            "fees_paid_sol_in_sample": total_fees_sol,
            # Solana burns half of the base fee; the rest plus all priority fees
            # accrue to the block leader.  This is the on-chain slice of "REV".
            "validator_fee_take_sol_in_sample": total_fees_sol * 0.5,
            "blocks": summaries,
        }

    return guarded(
        "Solana RPC: block sample",
        client.active,
        run,
        notes=[f"{config.BLOCK_SAMPLE_COUNT} blocks, ~{config.BLOCK_SAMPLE_SPACING} slots apart"],
    )
