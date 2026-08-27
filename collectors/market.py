"""CoinGecko public API collectors (no key, no attribution header required).

CoinGecko's anonymous tier is roughly 10-30 calls/minute and answers HTTP 429
when exceeded, so this module makes exactly three requests per run and relies
on :mod:`core.net`'s backoff to ride out a throttle.
"""

from __future__ import annotations

from typing import Any

from core import config
from core.net import FetchError, SourceResult, fetch_json, guarded


def collect_sol_market() -> SourceResult:
    """SOL price, market cap, volume, supply and multi-horizon price changes."""

    def run() -> dict[str, Any]:
        rows = fetch_json(config.COINGECKO_MARKETS)
        if not rows:
            raise FetchError("empty response for coin id 'solana'")
        row = rows[0]
        return {
            "price_usd": row.get("current_price"),
            "market_cap_usd": row.get("market_cap"),
            "market_cap_rank": row.get("market_cap_rank"),
            "fully_diluted_valuation_usd": row.get("fully_diluted_valuation"),
            "volume_24h_usd": row.get("total_volume"),
            "high_24h": row.get("high_24h"),
            "low_24h": row.get("low_24h"),
            "change_1h_pct": row.get("price_change_percentage_1h_in_currency"),
            "change_24h_pct": row.get("price_change_percentage_24h_in_currency"),
            "change_7d_pct": row.get("price_change_percentage_7d_in_currency"),
            "change_30d_pct": row.get("price_change_percentage_30d_in_currency"),
            "ath_usd": row.get("ath"),
            "ath_change_pct": row.get("ath_change_percentage"),
            "ath_date": row.get("ath_date"),
            "circulating_supply": row.get("circulating_supply"),
            "total_supply": row.get("total_supply"),
            "volume_to_mcap_pct": (
                row.get("total_volume") / row.get("market_cap") * 100
                if row.get("total_volume") and row.get("market_cap") else None
            ),
            "last_updated": row.get("last_updated"),
        }

    return guarded("CoinGecko: SOL market", config.COINGECKO_MARKETS, run)


def collect_price_history() -> SourceResult:
    """90 days of daily SOL close prices and USD volume, for the trend charts."""

    def run() -> dict[str, Any]:
        payload = fetch_json(config.COINGECKO_CHART)
        prices = [[int(t / 1000), float(v)] for t, v in (payload.get("prices") or [])]
        volumes = [[int(t / 1000), float(v)] for t, v in (payload.get("total_volumes") or [])]
        if not prices:
            raise FetchError("market_chart returned no price points")
        values = [p[1] for p in prices]
        return {
            "prices": prices,
            "volumes": volumes,
            "days": len(prices),
            "min_90d": min(values),
            "max_90d": max(values),
            "first_90d": values[0],
            "last": values[-1],
            "change_90d_pct": (values[-1] - values[0]) / values[0] * 100 if values[0] else None,
        }

    return guarded("CoinGecko: SOL 90d chart", config.COINGECKO_CHART, run)


def collect_ecosystem_tokens() -> SourceResult:
    """Top tokens tagged `solana-ecosystem` by market cap."""

    def run() -> list[dict[str, Any]]:
        rows = fetch_json(config.COINGECKO_ECOSYSTEM)
        out = []
        for row in rows or []:
            out.append({
                "symbol": (row.get("symbol") or "").upper(),
                "name": row.get("name"),
                "price_usd": row.get("current_price"),
                "market_cap_usd": row.get("market_cap"),
                "volume_24h_usd": row.get("total_volume"),
                "change_24h_pct": row.get("price_change_percentage_24h"),
            })
        if not out:
            raise FetchError("solana-ecosystem category returned no rows")
        return out

    return guarded("CoinGecko: ecosystem tokens", config.COINGECKO_ECOSYSTEM, run)
