"""DefiLlama public API collectors (no key required).

Covers the economic layer of the report: chain TVL and its history, protocol
league tables, DEX volume, chain fees and revenue (REV), stablecoin float and
tokenised real-world assets including equities.
"""

from __future__ import annotations

from typing import Any

from core import config
from core.net import FetchError, SourceResult, fetch_json, guarded

# Categories that hold assets on Solana but are not Solana DeFi: counting a
# centralised exchange's hot wallet as "TVL" would inflate the ecosystem number.
NON_DEFI_CATEGORIES = {"CEX", "Chain", "Bridge", "Canonical Bridge"}

# A dollar stablecoin is treated as depegged when it trades below this price.
DEPEG_FLOOR = 0.98
# ...and only when it is large enough for the reading to be meaningful; thin
# tokens routinely carry stale or illiquid quotes.
DEPEG_MIN_SIZE_USD = 25_000_000


def _pct_change(current: float | None, previous: float | None) -> float | None:
    """Percentage change from ``previous`` to ``current``, or None."""
    if current is None or not previous:
        return None
    return (current - previous) / previous * 100


def collect_chain_tvl() -> SourceResult:
    """Solana chain TVL now, plus the full daily history for trend charts."""

    def run() -> dict[str, Any]:
        history = fetch_json(config.LLAMA_CHAIN_TVL_HISTORY)
        if not history:
            raise FetchError("historicalChainTvl returned no points")
        series = [[int(p["date"]), float(p["tvl"])] for p in history]
        values = [p[1] for p in series]
        current = values[-1]

        def ago(days: int) -> float | None:
            return values[-1 - days] if len(values) > days else None

        rank = None
        chains = fetch_json(config.LLAMA_CHAINS)
        ordered = sorted(chains, key=lambda c: -(c.get("tvl") or 0))
        for index, chain in enumerate(ordered, start=1):
            if chain.get("name") == "Solana":
                rank = index
                current = chain.get("tvl") or current
                break
        total_all = sum(c.get("tvl") or 0 for c in chains) or None

        return {
            "tvl_usd": current,
            "tvl_rank": rank,
            "chain_count": len(chains),
            "share_of_all_chains_pct": (current / total_all * 100) if total_all else None,
            "change_1d_pct": _pct_change(current, ago(1)),
            "change_7d_pct": _pct_change(current, ago(7)),
            "change_30d_pct": _pct_change(current, ago(30)),
            "ath_usd": max(values),
            "history_daily": series[-365:],
        }

    return guarded("DefiLlama: chain TVL", config.LLAMA_CHAIN_TVL_HISTORY, run)


def collect_protocols() -> SourceResult:
    """Solana protocol league table, category mix and the RWA / equities slice."""

    def run() -> dict[str, Any]:
        protocols = fetch_json(config.LLAMA_PROTOCOLS, timeout=60.0)
        rows: list[dict[str, Any]] = []
        for p in protocols or []:
            chain_tvls = p.get("chainTvls") or {}
            tvl = chain_tvls.get("Solana")
            if not tvl or "Solana" not in (p.get("chains") or []):
                continue
            rows.append({
                "name": p.get("name"),
                "category": p.get("category"),
                "tvl_usd": float(tvl),
                "change_1d_pct": p.get("change_1d"),
                "change_7d_pct": p.get("change_7d"),
                "url": p.get("url"),
                "symbol": (p.get("symbol") or "").upper() if p.get("symbol") not in ("-", None) else None,
            })
        if not rows:
            raise FetchError("no protocols reported Solana TVL")
        rows.sort(key=lambda r: -r["tvl_usd"])

        defi = [r for r in rows if r["category"] not in NON_DEFI_CATEGORIES]
        categories: dict[str, float] = {}
        for r in defi:
            categories[r["category"]] = categories.get(r["category"], 0.0) + r["tvl_usd"]
        category_rows = [
            {"category": k, "tvl_usd": v} for k, v in sorted(categories.items(), key=lambda kv: -kv[1])
        ]
        rwa = [r for r in rows if r["category"] == "RWA"]
        # Tokenised equities: DefiLlama files them under RWA; these are the
        # issuers currently live on Solana with equity or equity-index exposure.
        equity_names = ("xstocks", "ondo global markets", "backed", "remora", "dinari", "swarm")
        equities = [r for r in rwa if any(n in (r["name"] or "").lower() for n in equity_names)]

        return {
            "protocol_count": len(rows),
            "defi_protocol_count": len(defi),
            "defi_tvl_usd": sum(r["tvl_usd"] for r in defi),
            "top_protocols": defi[:25],
            "categories": category_rows,
            "rwa_tvl_usd": sum(r["tvl_usd"] for r in rwa),
            "rwa_protocols": rwa[:15],
            "tokenized_equity_tvl_usd": sum(r["tvl_usd"] for r in equities),
            "tokenized_equity_protocols": equities,
            "excluded_categories": sorted(NON_DEFI_CATEGORIES),
        }

    return guarded("DefiLlama: protocols", config.LLAMA_PROTOCOLS, run)


def _dimension(url: str, name: str, label: str) -> SourceResult:
    """Shared parser for DefiLlama's 'dimension' endpoints (dexs, fees, ...)."""

    def run() -> dict[str, Any]:
        payload = fetch_json(url, timeout=60.0)
        chart = payload.get("totalDataChart") or []
        protocols = []
        for p in payload.get("protocols") or []:
            if p.get("total24h"):
                protocols.append({
                    "name": p.get("displayName") or p.get("name"),
                    "category": p.get("category"),
                    "total_24h_usd": p.get("total24h"),
                    "total_7d_usd": p.get("total7d"),
                    "change_1d_pct": p.get("change_1d"),
                })
        protocols.sort(key=lambda r: -(r["total_24h_usd"] or 0))
        total24 = payload.get("total24h")
        top = protocols[0] if protocols else None
        return {
            "label": label,
            "total_24h_usd": total24,
            "total_7d_usd": payload.get("total7d"),
            "total_30d_usd": payload.get("total30d"),
            "total_all_time_usd": payload.get("totalAllTime"),
            "change_1d_pct": payload.get("change_1d"),
            "change_7d_pct": payload.get("change_7d"),
            "change_30d_pct": payload.get("change_1m"),
            "protocol_count": len(protocols),
            "top_protocols": protocols[:15],
            "leader_share_pct": (
                top["total_24h_usd"] / total24 * 100 if top and total24 else None
            ),
            "history_daily": [[int(t), float(v)] for t, v in chart[-365:]],
        }

    return guarded(name, url, run)


def collect_dex_volume() -> SourceResult:
    """Aggregate Solana DEX volume and the per-DEX league table."""
    return _dimension(config.LLAMA_DEX, "DefiLlama: DEX volume", "DEX volume")


def collect_fees() -> SourceResult:
    """Chain-level fees paid and the protocols collecting them (REV inputs)."""
    return _dimension(config.LLAMA_FEES, "DefiLlama: fees & REV", "Fees")


def collect_stablecoins() -> SourceResult:
    """Stablecoin float on Solana, per asset, plus its 30-day history."""

    def run() -> dict[str, Any]:
        payload = fetch_json(config.LLAMA_STABLES, timeout=60.0)
        assets: list[dict[str, Any]] = []
        for asset in payload.get("peggedAssets") or []:
            on_solana = (asset.get("chainCirculating") or {}).get("Solana")
            if not on_solana:
                continue
            current = (on_solana.get("current") or {}).get("peggedUSD")
            prev_day = (on_solana.get("circulatingPrevDay") or {}).get("peggedUSD")
            prev_week = (on_solana.get("circulatingPrevWeek") or {}).get("peggedUSD")
            if not current:
                continue
            assets.append({
                "symbol": asset.get("symbol"),
                "name": asset.get("name"),
                "circulating_usd": float(current),
                "peg_mechanism": asset.get("pegMechanism"),
                "price": asset.get("price"),
                "change_1d_pct": _pct_change(current, prev_day),
                "change_7d_pct": _pct_change(current, prev_week),
                # Downside deviation only, and only for assets of material size.
                # Several dollar-pegged tokens on Solana accrue yield and are
                # designed to trade above $1 (USDY, sUSD); treating that as a
                # depeg would be a false alarm every single run. Breaking the
                # buck is the condition that carries risk.
                "depegged": (
                    asset.get("pegType") == "peggedUSD"
                    and isinstance(asset.get("price"), (int, float))
                    and asset["price"] < DEPEG_FLOOR
                    and float(current) >= DEPEG_MIN_SIZE_USD
                ),
            })
        if not assets:
            raise FetchError("no stablecoins reported circulation on Solana")
        assets.sort(key=lambda a: -a["circulating_usd"])
        total = sum(a["circulating_usd"] for a in assets)

        history: list[list[float]] = []
        try:
            chart = fetch_json(config.LLAMA_STABLE_CHART, timeout=60.0)
            history = [
                [int(p["date"]), float((p.get("totalCirculatingUSD") or {}).get("peggedUSD") or 0)]
                for p in chart[-365:]
            ]
        except Exception:  # noqa: BLE001 - the chart is an optional enrichment
            history = []

        return {
            "total_usd": total,
            "asset_count": len(assets),
            "assets": assets[:20],
            "top_share_pct": assets[0]["circulating_usd"] / total * 100 if total else None,
            "depegged": [a for a in assets if a["depegged"]],
            "history_daily": history,
        }

    return guarded("DefiLlama: stablecoins", config.LLAMA_STABLES, run)
