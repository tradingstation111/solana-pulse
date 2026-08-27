"""Self-contained interactive HTML dashboard.

The output is a single file with inline CSS, inline JavaScript and inline SVG
charts.  It has no external requests at all, so it renders identically from
GitHub Pages, from a local ``file://`` path, or from an offline archive.

Layout follows how the report is read rather than how it was collected: what
is wrong, then the headline numbers, then each domain, then the provenance and
method that let a reader check the work.
"""

from __future__ import annotations

import html as html_lib
import json
import os
from typing import Any, Iterable, Sequence

from analysis import history as history_store
from render import charts
from render.fmt import DASH, ago, num, pct, short_date, sol, truncate, usd
from render.theme import CSS, SCRIPT

SECTIONS = (
    ("alerts", "Alerts"), ("network", "Network"), ("validators", "Validators"),
    ("economy", "Economy"), ("growth", "Growth"), ("upgrades", "Upgrades & News"),
    ("sources", "Sources"), ("methodology", "Method"),
)

ALERT_ICON = {"critical": "●", "warning": "▲", "info": "◆"}


def esc(value: Any) -> str:
    """HTML-escape any value, rendering None as an em dash."""
    return html_lib.escape(str(value)) if value is not None else DASH


def _trend_class(value: Any) -> str:
    """CSS class for a signed change."""
    if not isinstance(value, (int, float)):
        return "flat"
    return "up" if value > 0 else ("down" if value < 0 else "flat")


def _kpi(label: str, value: str, sub: str = "", spark_values: Sequence[float] = (),
         color: str = charts.ACCENT, badge: str = "") -> str:
    """One KPI tile with an optional sparkline drawn from run history."""
    spark = charts.sparkline(list(spark_values), color=color) if len(spark_values) >= 2 else ""
    badge_html = f'<span class="pill">{esc(badge)}</span>' if badge else ""
    return (
        f'<div class="kpi"><div class="k"><span>{esc(label)}</span>{badge_html}</div>'
        f'<div class="v">{value}</div><div class="s">{sub}</div>{spark}</div>'
    )


def _stats(rows: Iterable[tuple[str, str]]) -> str:
    """Definition-style key/value list used inside cards."""
    items = "".join(
        f'<li><span class="k">{esc(k)}</span><span class="v">{v}</span></li>' for k, v in rows
    )
    return f'<ul class="stats">{items}</ul>'


def _table(headers: Sequence[tuple[str, bool]], rows: Sequence[Sequence[str]],
           *, scroll: bool = False) -> str:
    """Data table; ``headers`` pairs a label with whether the column is numeric."""
    if not rows:
        return '<div class="chart-empty">No rows available.</div>'
    head = "".join(f'<th class="{"num" if is_num else ""}">{esc(h)}</th>' for h, is_num in headers)
    body = "".join(
        "<tr>" + "".join(
            f'<td class="{"num" if headers[i][1] else ""}">{cell}</td>' for i, cell in enumerate(row)
        ) + "</tr>" for row in rows
    )
    cls = "tbl-wrap scroll-y" if scroll else "tbl-wrap"
    return f'<div class="{cls}"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def _card(title: str, sub: str, body: str, *, span: bool = False) -> str:
    """Panel wrapper."""
    return (f'<div class="card{" span2" if span else ""}"><h3>{esc(title)}</h3>'
            f'<p class="sub">{esc(sub)}</p>{body}</div>')


def _section(anchor: str, number: str, title: str, blurb: str, body: str) -> str:
    """Anchored page section with a numbered heading."""
    return (f'<section id="{anchor}"><div class="sec-head"><span class="n">{esc(number)}</span>'
            f'<h2>{esc(title)}</h2><p>{esc(blurb)}</p></div>{body}</section>')


def _degraded_note(snapshot: dict[str, Any], *names: str) -> str:
    """Visible banner naming any source that failed, with its exact error."""
    failed = [s for s in snapshot.get("sources", []) if not s["ok"] and s["name"] in names]
    if not failed:
        return ""
    lines = "<br>".join(f"⚠ {esc(s['name'])} unavailable — {esc(truncate(s['error'], 180))}"
                        for s in failed)
    return f'<div class="degraded">{lines}</div>'


def _source_names(snapshot: dict[str, Any], prefix: str) -> list[str]:
    """Every source name starting with ``prefix`` (used to build degradation banners)."""
    return [s["name"] for s in snapshot.get("sources", []) if s["name"].startswith(prefix)]


# --------------------------------------------------------------------------- #
# Sections
# --------------------------------------------------------------------------- #

def _alerts_section(snapshot: dict[str, Any]) -> str:
    """Alert cards plus detector status."""
    detection = snapshot.get("anomaly_detection", {})
    counts = detection.get("counts", {})
    alerts = snapshot.get("alerts", [])
    parts: list[str] = []

    if not detection.get("baseline_ready"):
        parts.append(
            f'<div class="degraded" style="border-color:#17415e;background:rgba(56,189,248,.07);'
            f'color:#9fd8f5">Baseline building: {detection.get("baseline_runs", 0)} of '
            f'{detection.get("method", {}).get("min_points")} runs collected. Statistical detection '
            f'switches on once enough history exists; threshold and cross-source rules are already '
            f'active.</div>'
        )
    if alerts:
        cards = "".join(
            f'<div class="alert {esc(a["severity"])}">'
            f'<span class="icon">{ALERT_ICON.get(a["severity"], "•")}</span>'
            f'<div class="body"><div class="t">{esc(a["title"])}'
            f'<span class="pill {"bad" if a["severity"] == "critical" else ("warn" if a["severity"] == "warning" else "info")}">'
            f'{esc(a["severity"])}</span>'
            f'<span class="pill">{esc(a["detector"])}</span>'
            + (f'<span class="pill">z {a["z_score"]:+.1f}</span>' if a.get("z_score") is not None else "")
            + f'</div><div class="d">{esc(a["detail"])}</div></div></div>'
            for a in alerts
        )
        parts.append(f'<div class="alerts">{cards}</div>')
    else:
        parts.append(
            '<div class="quiet"><b>No anomalies detected.</b><br>Every monitored metric is inside '
            'its expected range, no threshold rule fired, and no cross-source divergence was found.</div>'
        )
    parts.append(
        f'<p class="note">{counts.get("critical", 0)} critical · {counts.get("warning", 0)} warning · '
        f'{counts.get("info", 0)} informational — from {detection.get("metrics_scored", 0)} '
        f'statistically scored metrics over {detection.get("baseline_runs", 0)} runs of history, '
        f'plus threshold and cross-source detectors. Method is described in section 08.</p>'
    )
    return "".join(parts)


def _network_section(snapshot: dict[str, Any], hist: list[dict[str, Any]]) -> str:
    """Throughput, slot time, epoch progress and locally-parsed block statistics."""
    s = snapshot.get("sections", {})
    m = snapshot.get("metrics", {})
    cluster = s.get("cluster") or {}
    perf = s.get("performance") or {}
    sample = s.get("blocks") or {}
    status = s.get("status") or {}

    banner = _degraded_note(snapshot, *_source_names(snapshot, "Solana RPC"),
                            *_source_names(snapshot, "Solana Statuspage"))

    tps_points = [x["tps"] for x in perf.get("samples", [])]
    slot_points = [x["slot_time_ms"] for x in perf.get("samples", [])]
    cards = [
        _card("Throughput, last 30 minutes",
              "Transactions per second from getRecentPerformanceSamples, one point per minute.",
              charts.area_chart(
                  [[i, v] for i, v in enumerate(tps_points)] if tps_points else [],
                  label="TPS", color=charts.ACCENT, height=180,
                  x_labels=(f"{len(tps_points)} min ago", "now"))
              if tps_points else '<div class="chart-empty">Performance samples unavailable.</div>',
              span=True),
        _card("Cluster",
              f"Answered by {cluster.get('endpoint', DASH)}",
              _stats([
                  ("Health", f'<span class="pill {"ok" if cluster.get("health") == "ok" else "bad"}">'
                             f'{esc(cluster.get("health", "unknown"))}</span>'),
                  ("Status page", f'<span class="pill {"ok" if status.get("indicator") == "none" else "warn"}">'
                                  f'{esc(status.get("description", "unknown"))}</span>'),
                  ("solana-core", esc(cluster.get("solana_core"))),
                  ("Feature set", num(cluster.get("feature_set"))),
                  ("Absolute slot", num(cluster.get("absolute_slot"))),
                  ("Block height", num(cluster.get("block_height"))),
                  ("Lifetime transactions", num(cluster.get("transaction_count"))),
              ])),
        _card("Epoch progress",
              f"Epoch {num(cluster.get('epoch'))} · {num(cluster.get('epoch_slots_remaining'))} slots remain",
              charts.gauge(cluster.get("epoch_progress_pct"), label="epoch progress") +
              _stats([
                  ("Slot in epoch", f"{num(cluster.get('slot_index'))} / {num(cluster.get('slots_in_epoch'))}"),
                  ("Estimated time left", _epoch_eta(cluster, m)),
                  ("Mean slot time", num(perf.get("slot_time_ms_mean"), 1, " ms")),
                  ("Peak TPS in window", num(perf.get("tps_max"), 0)),
              ])),
        _card("Slot time, last 30 minutes",
              "Milliseconds per slot; the protocol targets roughly 400 ms.",
              charts.area_chart([[i, v] for i, v in enumerate(slot_points)] if slot_points else [],
                                label="Slot time", color=charts.ACCENT_ALT, height=170,
                                x_labels=(f"{len(slot_points)} min ago", "now"))),
    ]

    run_tps = [[i, r["tps"]] for i, r in enumerate(hist) if isinstance(r.get("tps"), (int, float))]
    if len(run_tps) >= 2:
        cards.append(_card("Throughput across collection runs",
                           f"One point per run — {len(run_tps)} runs recorded so far. This is the "
                           f"series the anomaly baseline is built from.",
                           charts.area_chart(run_tps, label="TPS per run", color=charts.ACCENT,
                                             height=170,
                                             x_labels=("run 1", f"run {len(run_tps)}"))))

    if sample:
        blocks_rows = [
            [num(b.get("slot")), num(b.get("tx_count")), num(b.get("user_tx_count")),
             num(b.get("unique_fee_payers")), pct(b.get("failure_rate_pct"), 1),
             num(b.get("median_user_fee_lamports"))]
            for b in sample.get("blocks", [])
        ]
        cards.append(_card(
            "Direct block sampling",
            f"{sample.get('blocks_sampled')} finalised blocks downloaded in full and parsed locally, "
            f"spanning {num(sample.get('sample_span_seconds'))} seconds of chain time. Nothing here "
            f"comes from an aggregator.",
            _stats([
                ("Median user transaction fee",
                 f"{num(sample.get('median_tx_fee_lamports'))} lamports "
                 f"<span style='color:var(--dim)'>({usd(m.get('median_tx_fee_usd'), 6)})</span>"),
                ("90th percentile fee", f"{num(sample.get('p90_tx_fee_lamports'))} lamports"),
                ("Median priority fee", f"{num(sample.get('median_priority_fee_lamports'))} lamports"),
                ("Priority share of fees paid", pct(sample.get("priority_fee_share_pct"), 1)),
                ("On-chain failure rate", pct(sample.get("tx_failure_rate_pct"), 1)),
                ("Vote share of all transactions", pct(sample.get("vote_tx_share_pct"), 1)),
                ("Average transactions per block", num(sample.get("avg_txs_per_block"))),
                ("Fees paid in sample", sol(sample.get("fees_paid_sol_in_sample"), 4)),
            ]) +
            _table([("Slot", True), ("Txs", True), ("User txs", True), ("Payers", True),
                    ("Failed", True), ("Median fee", True)], blocks_rows),
            span=True))

    return banner + f'<div class="grid g2">{"".join(cards)}</div>'


def _epoch_eta(cluster: dict[str, Any], metrics: dict[str, Any]) -> str:
    """Estimated wall-clock time until the current epoch ends."""
    remaining = cluster.get("epoch_slots_remaining")
    slot_ms = metrics.get("slot_time_ms")
    if not isinstance(remaining, (int, float)) or not isinstance(slot_ms, (int, float)) or slot_ms <= 0:
        return DASH
    seconds = remaining * slot_ms / 1000
    hours, minutes = divmod(int(seconds // 60), 60)
    days, hours = divmod(hours, 24)
    return (f"{days}d {hours}h {minutes}m" if days else f"{hours}h {minutes}m")


def _validators_section(snapshot: dict[str, Any]) -> str:
    """Stake concentration, delinquency, commissions and client diversity."""
    s = snapshot.get("sections", {})
    v = s.get("validators")
    nodes = s.get("cluster_nodes")
    banner = _degraded_note(snapshot, "Solana RPC: vote accounts", "Solana RPC: cluster nodes")
    if not v:
        return banner + '<div class="chart-empty">Validator data unavailable this run.</div>'

    cards = [
        _card("Stake concentration",
              "How much stake sits with how few operators. Higher Nakamoto is more decentralised.",
              _stats([
                  ("Nakamoto coefficient", f'<b style="color:var(--accent)">{num(v.get("nakamoto_coefficient"))}</b>'),
                  ("Largest validator", pct(v.get("top1_stake_pct"), 2)),
                  ("Top 10 validators", pct(v.get("top10_stake_pct"), 2)),
                  ("Top 20 validators", pct(v.get("top20_stake_pct"), 2)),
                  ("Top 100 validators", pct(v.get("top100_stake_pct"), 2)),
                  ("Median validator stake", sol(v.get("median_stake_sol"))),
                  ("Total activated stake", sol(v.get("total_stake_sol"))),
              ])),
        _card("Delinquency",
              "Validators that have stopped voting. Consensus halts if delinquent stake passes 33%.",
              _stats([
                  ("Active validators", num(v.get("active_count"))),
                  ("Delinquent validators", num(v.get("delinquent_count"))),
                  ("Delinquent stake", pct(v.get("delinquent_stake_pct"), 3)),
                  ("Delinquent stake amount", sol(v.get("delinquent_stake_sol"))),
                  ("Headroom to 33% halt", pct(33.3 - (v.get("delinquent_stake_pct") or 0), 2)),
              ]) +
              _table([("Largest delinquent", False), ("Stake", True), ("Share", True)],
                     [[f'<span class="mono">{esc(truncate(r["vote_pubkey"], 14))}</span>',
                       sol(r["stake_sol"]), pct(r["stake_pct"], 4)]
                      for r in (v.get("top_delinquent") or [])[:6]]
                     or [["<span style='color:var(--dim)'>none reported</span>", DASH, DASH]])),
        _card("Commission distribution",
              "Share of block rewards each validator keeps, bucketed.",
              charts.bar_chart(list((v.get("commission_buckets") or {}).items()), color="palette")),
    ]
    if nodes:
        cards.append(_card(
            "Validator client diversity",
            f"{num(nodes.get('gossip_node_count'))} nodes visible over gossip, "
            f"{num(nodes.get('distinct_versions'))} distinct versions. A monoculture means one "
            f"consensus bug reaches nearly every node.",
            charts.donut([(r["client"], r["nodes"]) for r in nodes.get("clients", [])[:8]],
                         centre_value=f"{nodes.get('dominant_client_pct', 0):.0f}%",
                         centre_label=str(nodes.get("dominant_client") or ""))))
        cards.append(_card(
            "Software versions in gossip", "Top versions by node count.",
            _table([("Version", False), ("Nodes", True), ("Share", True)],
                   [[f'<span class="mono">{esc(r["version"])}</span>', num(r["nodes"]),
                     pct(r["share_pct"], 1)] for r in nodes.get("versions", [])[:10]], scroll=True)))

    controls = (
        '<div class="controls">'
        '<input type="search" id="vsearch" placeholder="Search vote or node pubkey…" '
        'aria-label="Search validators">'
        '<select id="vsort" aria-label="Sort validators">'
        '<option value="stake">Stake, high to low</option>'
        '<option value="stake_asc">Stake, low to high</option>'
        '<option value="commission">Commission, low to high</option>'
        '<option value="commission_desc">Commission, high to low</option>'
        '</select>'
        '<button class="ghost" id="vdelinq" aria-pressed="false">Delinquent only</button>'
        '<span class="count" id="vcount"></span></div>'
    )
    table = (
        '<div class="tbl-wrap scroll-y"><table><thead><tr>'
        '<th class="num">#</th><th>Vote account</th><th>Node</th><th class="num">Stake (SOL)</th>'
        '<th class="num">Share</th><th class="num">Commission</th><th>Status</th>'
        '</tr></thead><tbody id="vrows"></tbody></table></div>'
        '<div style="margin-top:10px"><button class="ghost" id="vmore">Load more</button></div>'
    )
    cards.append(_card("Validator directory",
                       f"All {num(v.get('validator_count'))} vote accounts. Search and sort run "
                       f"entirely in the page — no requests are made.",
                       controls + table, span=True))
    return banner + f'<div class="grid g2">{"".join(cards)}</div>'


def _economy_section(snapshot: dict[str, Any], hist: list[dict[str, Any]]) -> str:
    """Price, supply, TVL, DEX volume, fees/REV and stablecoins."""
    s = snapshot.get("sections", {})
    m = snapshot.get("metrics", {})
    market = s.get("market") or {}
    chart = s.get("price_history") or {}
    tvl = s.get("tvl") or {}
    protocols = s.get("protocols") or {}
    dex = s.get("dex") or {}
    fees = s.get("fees") or {}
    stables = s.get("stablecoins") or {}
    supply = s.get("supply") or {}

    banner = _degraded_note(snapshot, *_source_names(snapshot, "CoinGecko"),
                            *_source_names(snapshot, "DefiLlama"))
    cards = [
        _card("SOL price, 90 days",
              f"Daily close from CoinGecko. Range {usd(chart.get('min_90d'))} – "
              f"{usd(chart.get('max_90d'))}, {pct(chart.get('change_90d_pct'), 1, True)} over the window.",
              charts.area_chart(chart.get("prices", []), label="SOL price", color=charts.ACCENT,
                                value_format="usd", height=200),
              span=True),
        _card("Market", "CoinGecko public API.",
              _stats([
                  ("Price", f'<b>{usd(market.get("price_usd"))}</b>'),
                  ("1h", f'<span class="{_trend_class(market.get("change_1h_pct"))}">'
                         f'{pct(market.get("change_1h_pct"), 2, True)}</span>'),
                  ("24h", f'<span class="{_trend_class(market.get("change_24h_pct"))}">'
                          f'{pct(market.get("change_24h_pct"), 2, True)}</span>'),
                  ("7d", f'<span class="{_trend_class(market.get("change_7d_pct"))}">'
                         f'{pct(market.get("change_7d_pct"), 2, True)}</span>'),
                  ("30d", f'<span class="{_trend_class(market.get("change_30d_pct"))}">'
                          f'{pct(market.get("change_30d_pct"), 2, True)}</span>'),
                  ("Market cap", f'{usd(market.get("market_cap_usd"))} (#{num(market.get("market_cap_rank"))})'),
                  ("24h volume", usd(market.get("volume_24h_usd"))),
                  ("Volume / market cap", pct(market.get("volume_to_mcap_pct"), 2)),
                  ("From all-time high", f'{pct(market.get("ath_change_pct"), 1)} '
                                         f'<span style="color:var(--dim)">({short_date(market.get("ath_date"))})</span>'),
              ])),
        _card("Supply, staking and inflation", "Solana RPC getSupply and getInflationRate.",
              _stats([
                  ("Total supply", sol(supply.get("total_supply_sol"))),
                  ("Circulating", f'{sol(supply.get("circulating_supply_sol"))} '
                                  f'({pct(supply.get("circulating_pct"), 1)})'),
                  ("Staked", f'{sol(m.get("total_stake_sol"))} ({pct(m.get("staking_ratio_pct"), 1)})'),
                  ("Value staked", usd(m.get("staked_value_usd"))),
                  ("Inflation rate", pct(supply.get("inflation_total_pct"), 3)),
                  ("Market cap / TVL", num(m.get("mcap_to_tvl"), 2)),
                  ("Annualised fees / market cap", pct(m.get("annualised_fee_to_mcap_pct"), 2)),
              ])),
        _card("Total value locked",
              f"Rank #{num(tvl.get('tvl_rank'))} of {num(tvl.get('chain_count'))} chains · "
              f"{pct(tvl.get('share_of_all_chains_pct'), 2)} of all on-chain TVL.",
              charts.area_chart(tvl.get("history_daily", []), label="Solana TVL",
                                color=charts.ACCENT_ALT, value_format="usd", height=185) +
              _stats([
                  ("Now", f'<b>{usd(tvl.get("tvl_usd"))}</b>'),
                  ("24h", f'<span class="{_trend_class(tvl.get("change_1d_pct"))}">'
                          f'{pct(tvl.get("change_1d_pct"), 2, True)}</span>'),
                  ("7d", f'<span class="{_trend_class(tvl.get("change_7d_pct"))}">'
                         f'{pct(tvl.get("change_7d_pct"), 2, True)}</span>'),
                  ("30d", f'<span class="{_trend_class(tvl.get("change_30d_pct"))}">'
                          f'{pct(tvl.get("change_30d_pct"), 2, True)}</span>'),
                  ("All-time high", usd(tvl.get("ath_usd"))),
              ]), span=True),
        _card("TVL by category",
              "Centralised-exchange wallets and bridges are excluded — they hold assets on Solana "
              "without being Solana DeFi.",
              charts.bar_chart([(r["category"], r["tvl_usd"]) for r in protocols.get("categories", [])[:8]],
                               color="palette", value_format="usd")),
        _card("Top protocols by TVL", f"{num(protocols.get('defi_protocol_count'))} DeFi protocols tracked.",
              _table([("Protocol", False), ("Category", False), ("TVL", True), ("24h", True), ("7d", True)],
                     [[esc(r["name"]), f'<span class="pill">{esc(r["category"])}</span>',
                       usd(r["tvl_usd"]),
                       f'<span class="{_trend_class(r.get("change_1d_pct"))}">{pct(r.get("change_1d_pct"), 1, True)}</span>',
                       f'<span class="{_trend_class(r.get("change_7d_pct"))}">{pct(r.get("change_7d_pct"), 1, True)}</span>']
                      for r in protocols.get("top_protocols", [])[:20]], scroll=True)),
        _card("DEX volume, 12 months",
              f"{usd(dex.get('total_24h_usd'))} in 24h · {usd(dex.get('total_7d_usd'))} in 7d · "
              f"{usd(dex.get('total_30d_usd'))} in 30d.",
              charts.area_chart(dex.get("history_daily", []), label="DEX volume",
                                color=charts.ACCENT, value_format="usd", height=185) +
              _table([("Venue", False), ("24h", True), ("Share", True)],
                     [[esc(r["name"]), usd(r["total_24h_usd"]),
                       pct(r["total_24h_usd"] / dex["total_24h_usd"] * 100, 1)
                       if dex.get("total_24h_usd") else DASH]
                      for r in dex.get("top_protocols", [])[:8]]), span=True),
        _card("Fees and Real Economic Value",
              f"Fees paid on Solana: {usd(fees.get('total_24h_usd'))} in 24h, "
              f"{usd(fees.get('total_30d_usd'))} in 30d, {usd(fees.get('total_all_time_usd'))} lifetime.",
              charts.area_chart(fees.get("history_daily", []), label="Chain fees",
                                color="#f59e0b", value_format="usd", height=185) +
              _stats([
                  ("24h change", f'<span class="{_trend_class(fees.get("change_1d_pct"))}">'
                                 f'{pct(fees.get("change_1d_pct"), 1, True)}</span>'),
                  ("7d change", f'<span class="{_trend_class(fees.get("change_7d_pct"))}">'
                                f'{pct(fees.get("change_7d_pct"), 1, True)}</span>'),
                  ("Fees per DEX volume", num(m.get("fee_per_dex_volume_bps"), 2, " bps")),
                  ("Median transaction fee (on-chain)", f'{num(m.get("median_tx_fee_lamports"))} lamports'),
              ]), span=True),
        _card("Stablecoins on Solana",
              f"{usd(stables.get('total_usd'))} across {num(stables.get('asset_count'))} assets · "
              f"largest holds {pct(stables.get('top_share_pct'), 1)}.",
              charts.area_chart(stables.get("history_daily", []), label="Stablecoin float",
                                color="#38bdf8", value_format="usd", height=170) +
              _table([("Asset", False), ("On Solana", True), ("24h", True), ("7d", True)],
                     [[f'<b>{esc(r["symbol"])}</b> <span style="color:var(--dim)">{esc(truncate(r["name"], 18))}</span>',
                       usd(r["circulating_usd"]),
                       f'<span class="{_trend_class(r.get("change_1d_pct"))}">{pct(r.get("change_1d_pct"), 2, True)}</span>',
                       f'<span class="{_trend_class(r.get("change_7d_pct"))}">{pct(r.get("change_7d_pct"), 2, True)}</span>']
                      for r in stables.get("assets", [])[:12]], scroll=True), span=True),
    ]
    return banner + f'<div class="grid g2">{"".join(cards)}</div>'


def _growth_section(snapshot: dict[str, Any]) -> str:
    """RWA and tokenised equities, wallet activity, ecosystem tokens, watched programs."""
    s = snapshot.get("sections", {})
    m = snapshot.get("metrics", {})
    protocols = s.get("protocols") or {}
    sample = s.get("blocks") or {}
    tokens = s.get("ecosystem_tokens") or []
    accounts = s.get("accounts") or []

    cards = [
        _card("Tokenised real-world assets",
              f"{usd(protocols.get('rwa_tvl_usd'))} on Solana, of which "
              f"{usd(protocols.get('tokenized_equity_tvl_usd'))} is tokenised equity exposure "
              f"(xStocks, Ondo Global Markets and peers).",
              charts.bar_chart([(r["name"], r["tvl_usd"]) for r in protocols.get("rwa_protocols", [])[:8]],
                               color="palette", value_format="usd") +
              _table([("Issuer", False), ("Value", True), ("24h", True)],
                     [[esc(r["name"]), usd(r["tvl_usd"]),
                       f'<span class="{_trend_class(r.get("change_1d_pct"))}">{pct(r.get("change_1d_pct"), 1, True)}</span>']
                      for r in protocols.get("rwa_protocols", [])[:10]]), span=True),
        _card("Wallet activity, measured on chain",
              "Distinct fee payers counted directly in the sampled blocks. The window estimate uses "
              "Chapman capture-recapture over two disjoint halves of the sample.",
              _stats([
                  ("Unique fee payers per block", num(sample.get("avg_unique_payers_per_block"))),
                  ("Unique fee payers across sample", num(sample.get("unique_payers_in_sample"))),
                  ("Wallets seen in both halves", num(sample.get("payer_recapture_overlap"))),
                  ("Window population estimate", num(sample.get("window_active_wallet_estimate"))),
                  ("New-wallet discovery rate", num(sample.get("new_payer_discovery_rate_per_s"), 2, " /s")),
                  ("Projected user transactions per day", num(m.get("projected_daily_user_txs"))),
              ]) +
              '<p class="note">Heavy automated wallets appear in every block, so the population '
              'estimate over-weights them. Read it as an order of magnitude for the sampling window, '
              'not as a daily active-user count.</p>'),
        _card("Largest ecosystem tokens", "CoinGecko `solana-ecosystem` category, by market cap.",
              _table([("Token", False), ("Price", True), ("Market cap", True), ("24h", True)],
                     [[f'<b>{esc(r["symbol"])}</b> <span style="color:var(--dim)">{esc(truncate(r["name"], 16))}</span>',
                       usd(r["price_usd"], 4), usd(r["market_cap_usd"]),
                       f'<span class="{_trend_class(r.get("change_24h_pct"))}">{pct(r.get("change_24h_pct"), 1, True)}</span>']
                      for r in tokens[:12]], scroll=True)),
        _card("Watched programs", "Balance and signature activity for well-known mainnet programs.",
              _table([("Program", False), ("Balance", True), ("Sig rate", True), ("Failed", True)],
                     [[f'{esc(r["label"])}<br><span class="mono" style="color:var(--dim);font-size:11px">'
                       f'{esc(truncate(r["address"], 22))}</span>',
                       sol(r.get("balance_sol"), 3),
                       (num(r.get("sig_rate_per_min"), 0, "/min") + "+"
                        if r.get("sig_rate_is_lower_bound") else num(r.get("sig_rate_per_min"), 1, "/min")),
                       pct(r.get("failure_rate_pct"), 0)]
                      for r in accounts]) +
              '<p class="note">' +
              " · ".join(f'<b>{esc(r["label"])}</b>: {esc(r.get("why", ""))}' for r in accounts) +
              ' — a rate marked with "+" is a lower bound: block timestamps have one-second '
              'resolution, and the program produced the whole 100-signature sample inside a '
              'single second.</p>', span=True),
    ]
    return f'<div class="grid g2">{"".join(cards)}</div>'


def _upgrades_section(snapshot: dict[str, Any]) -> str:
    """SIMD governance, client releases, incidents and ecosystem news."""
    s = snapshot.get("sections", {})
    simds = s.get("simds") or {}
    accepted = s.get("accepted_simds") or {}
    releases = s.get("releases") or {}
    newsdata = s.get("news") or {}
    status = s.get("status") or {}
    banner = _degraded_note(snapshot, *_source_names(snapshot, "GitHub"),
                            *_source_names(snapshot, "Ecosystem news"))

    cards = []
    if accepted.get("tracked_upgrades"):
        rows = [[
            f'<b>{esc(u["label"])}</b>' + (f' <span class="mono" style="color:var(--dim)">SIMD-{u["simd"]:04d}</span>'
                                          if u.get("simd") is not None else ""),
            f'<span class="pill {"ok" if u["accepted"] else "info"}">'
            f'{"accepted" if u["accepted"] else "not yet accepted"}</span>',
            f'<span style="color:var(--muted)">{esc(u["why"])}</span>',
            f'<a href="{esc(u["url"])}">document</a>' if u.get("url") else DASH,
        ] for u in accepted["tracked_upgrades"]]
        cards.append(_card(
            "Named upgrades being tracked",
            f"Status of the protocol changes the ecosystem is waiting on. "
            f"{num(accepted.get('accepted_count'))} SIMDs have been accepted in total.",
            _table([("Upgrade", False), ("Status", False), ("Why it matters", False), ("", False)], rows),
            span=True))
    if simds.get("highlighted"):
        cards.append(_card(
            "Proposals under close watch",
            "SIMDs matching the tracked keywords: " + ", ".join(simds.get("highlight_keywords", [])),
            _table([("PR", True), ("Title", False), ("State", False), ("Updated", False)],
                   [[f'<a href="{esc(r["url"])}">#{r["number"]}</a>', esc(truncate(r["title"], 90)),
                     f'<span class="pill {"ok" if r["state"] == "merged" else "info"}">{esc(r["state"])}</span>',
                     short_date(r.get("updated_at"))]
                    for r in simds["highlighted"][:8]]), span=True))
    cards.append(_card(
        "Open SIMDs", f"{num(simds.get('open_count'))} open proposals, most recently updated first.",
        _table([("PR", True), ("Title", False), ("Author", False)],
               [[f'<a href="{esc(r["url"])}">#{r["number"]}</a>', esc(truncate(r["title"], 78)),
                 esc(r.get("author"))] for r in simds.get("open", [])[:14]], scroll=True)))
    cards.append(_card(
        "Recently merged SIMDs", "Accepted protocol changes.",
        _table([("PR", True), ("Title", False), ("Merged", False)],
               [[f'<a href="{esc(r["url"])}">#{r["number"]}</a>', esc(truncate(r["title"], 78)),
                 short_date(r.get("merged_at"))] for r in simds.get("recently_merged", [])[:14]],
               scroll=True)))
    if accepted.get("accepted_recent"):
        cards.append(_card(
            "Most recent accepted SIMDs", "Highest-numbered proposal documents in the repository.",
            _table([("SIMD", True), ("Title", False)],
                   [[f'<a href="{esc(d["url"])}">{d["simd"]:04d}</a>' if d.get("simd") is not None
                     else DASH, esc(truncate(d["title"], 70))]
                    for d in accepted["accepted_recent"][:12]], scroll=True)))
    if releases:
        rows = []
        for client in releases.get("clients", []):
            latest = client.get("latest_stable") or {}
            rows.append([esc(client["client"]),
                         f'<a href="{esc(latest.get("url"))}" class="mono">{esc(latest.get("tag"))}</a>',
                         short_date(latest.get("published"))])
        cards.append(_card("Validator client releases",
                           "Latest stable release published by each implementation.",
                           _table([("Client", False), ("Latest stable", False), ("Published", False)], rows)))
    if status.get("incidents"):
        cards.append(_card("Recent incidents", "From Solana's public status page.",
                           _table([("Incident", False), ("Impact", False), ("Opened", False)],
                                  [[esc(i["name"]), f'<span class="pill warn">{esc(i["impact"])}</span>',
                                    short_date(i.get("created_at"))] for i in status["incidents"]])))
    if newsdata.get("items"):
        items = "".join(
            f'<li><div class="meta"><span>{esc(short_date(i.get("published")))}</span>'
            f'<span>{esc(i["source"])}</span></div>'
            f'<div class="ttl"><a href="{esc(i["link"])}">{esc(truncate(i["title"], 130))}</a></div>'
            + (f'<div class="sum">{esc(truncate(i["summary"], 190))}</div>' if i.get("summary") else "")
            + "</li>"
            for i in newsdata["items"][:18]
        )
        note = ""
        if newsdata.get("failed_feeds"):
            note = f'<p class="note">Feeds unavailable this run: {esc("; ".join(newsdata["failed_feeds"]))}</p>'
        cards.append(_card("Ecosystem news",
                           f"Merged from {num(newsdata.get('feed_count'))} public RSS and Atom feeds, "
                           f"parsed with the standard library.",
                           f'<ul class="news">{items}</ul>' + note, span=True))
    accounts = "".join(f'<a href="{esc(a["url"])}" class="pill" style="margin-right:6px">{esc(a["handle"])}</a>'
                       for a in newsdata.get("x_accounts", []))
    cards.append(_card(
        "Social signal", "Why X/Twitter sentiment is absent.",
        '<p class="note" style="font-size:12.6px">X has no keyless, terms-compliant read path, and '
        'the public mirrors that exist are unreliable enough that any number taken from them would '
        'be a guess presented as data. Rather than fabricate sentiment, the report links the official '
        'accounts and states the gap. If a key is ever acceptable, one collector module is the whole '
        'change.</p><div style="margin-top:8px">' + accounts + '</div>'))
    return banner + f'<div class="grid g2">{"".join(cards)}</div>'


def _sources_section(snapshot: dict[str, Any]) -> str:
    """Per-source status, latency and freshness."""
    rows = [
        [esc(src["name"]),
         f'<span class="pill {"ok" if src["ok"] else "bad"}">{"live" if src["ok"] else "unavailable"}</span>',
         num(src["elapsed_ms"], 0, " ms"), esc(ago(src["fetched_at"])),
         f'<span class="mono" style="font-size:11px;color:var(--dim)">'
         f'{esc(truncate(src.get("error") or "; ".join(src.get("notes") or []) or src["url"], 92))}</span>']
        for src in snapshot.get("sources", [])
    ]
    summary = snapshot.get("source_summary", {})
    generator = snapshot.get("generator", {})
    return (
        f'<div class="grid g2">'
        + _card("Source ledger",
                f"{summary.get('ok')} of {summary.get('total')} sources answered this run. "
                f"Each row shows the exact latency and, on failure, the exact error.",
                _table([("Source", False), ("Status", False), ("Latency", True), ("Fetched", False),
                        ("Detail", False)], rows), span=True)
        + _card("Run", "Generator and environment.",
                _stats([
                    ("Generated (UTC)", esc(snapshot.get("generated_at"))),
                    ("Your local time", '<span id="localtime">—</span>'),
                    ("Run time", num(snapshot.get("runtime_seconds"), 2, " s")),
                    ("RPC endpoint used", f'<span class="mono" style="font-size:11px">'
                                          f'{esc(generator.get("rpc_endpoint"))}</span>'),
                    ("RPC calls made", num(generator.get("rpc_calls"))),
                    ("Python", esc(generator.get("python"))),
                    ("Dependencies", esc(generator.get("dependencies"))),
                ]))
        + _card("History", "The file the anomaly baseline is computed from.",
                _stats([
                    ("Runs recorded", num(snapshot.get("history", {}).get("records"))),
                    ("First run", esc(snapshot.get("history", {}).get("first_run"))),
                    ("Store", f'<span class="mono">{esc(snapshot.get("history", {}).get("path"))}</span>'),
                    ("Format", "JSON Lines, one object per run"),
                    ("Downloads", '<a href="report.json">report.json</a> · '
                                  '<a href="latest.json">latest.json</a> · '
                                  '<a href="report.md">report.md</a>'),
                ]))
        + '</div>'
    )


def _methodology_section(snapshot: dict[str, Any]) -> str:
    """Collapsible explanation of collection, detection and limits."""
    method = snapshot.get("anomaly_detection", {}).get("method", {})
    return f"""
<details class="method" open><summary>How this report is produced</summary><div class="inner">
<h4>Collection</h4>
<p>Every source is fetched independently and wrapped so that a failure downgrades exactly one
section instead of the run. Solana RPC calls fail over across public endpoints; everything else is
a public HTTP API or an RSS/Atom feed. No API key is used anywhere, and the only dependency is the
Python standard library — <code>urllib</code>, <code>json</code>, <code>xml.etree</code>,
<code>statistics</code>, <code>html</code>.</p>

<h4>Anomaly detection</h4>
<p>Three detectors run on every report.</p>
<p><b>1. Statistical.</b> The modified z-score <code>{esc(method.get('statistical'))}</code> is
computed for each watched metric over the last {esc(method.get('window_runs'))} runs. Median and
median absolute deviation replace mean and standard deviation, because a single earlier spike would
otherwise inflate the baseline and hide the next one. |z| ≥ {esc(method.get('warn_z'))} raises a
warning and |z| ≥ {esc(method.get('critical_z'))} is critical. Metrics are direction-aware, so a
rising Nakamoto coefficient never alerts, and a minimum relative-change floor suppresses alerts on
movements that are statistically odd but practically trivial. Nothing fires until
{esc(method.get('min_points'))} runs of history exist.</p>
<p><b>2. Threshold rules.</b> Conditions that are bad regardless of history, which statistics cannot
catch because a permanently broken cluster has a perfectly stable baseline: unhealthy RPC, slot time
over 600 ms, delinquent stake over 2%, on-chain failure rate over 65%, client monoculture over 85%,
Nakamoto coefficient under 15, a stablecoin more than 2% off peg.</p>
<p><b>3. Cross-source correlation.</b> Signals that exist only because several sources are held at
once: TVL diverging from price, the fee-to-DEX-volume ratio shifting, throughput and failure rate
rising together, stablecoin share of TVL rotating. A single-source dashboard cannot make these
checks.</p>

<h4>Direct block sampling</h4>
<p>Median fee, priority-fee share, failure rate and wallet counts come from finalised blocks
downloaded in full over RPC and parsed locally — not from an aggregator. The active-wallet figure
uses Chapman's capture-recapture estimator over two disjoint halves of the sample; because automated
wallets appear in every block, it over-weights them and is an order-of-magnitude reading for the
sampling window rather than a daily user count.</p>

<h4>Limits, stated plainly</h4>
<p>Aggregated economic figures (TVL, DEX volume, fees, stablecoin float) carry their providers'
methodologies and later revisions. RPC readings are point-in-time and reflect whichever endpoint
answered. Centralised-exchange wallets and bridges are excluded from DeFi TVL. X/Twitter sentiment
is not collected because no keyless, terms-compliant path exists. Nothing in this report is
estimated where it could be measured, and every estimate says so where it appears.</p>
</div></details>"""


# --------------------------------------------------------------------------- #
# Page assembly
# --------------------------------------------------------------------------- #

def _kpi_strip(snapshot: dict[str, Any], hist: list[dict[str, Any]]) -> str:
    """Headline tiles with sparklines drawn from the run history."""
    m = snapshot.get("metrics", {})
    s = snapshot.get("sections", {})
    market = s.get("market") or {}
    tvl = s.get("tvl") or {}
    dex = s.get("dex") or {}
    fees = s.get("fees") or {}
    v = s.get("validators") or {}

    def spark(metric: str) -> list[float]:
        return [value for _, value in history_store.series(hist, metric, 60)]

    def change_sub(value: Any, window: str) -> str:
        return f'<span class="{_trend_class(value)}">{pct(value, 2, True)}</span> {window}'

    tiles = [
        _kpi("Throughput", num(m.get("tps"), 0), f"{num(m.get('non_vote_tps'), 0)} non-vote TPS",
             spark("tps"), charts.ACCENT),
        _kpi("Slot time", num(m.get("slot_time_ms"), 0, " ms"), "~400 ms target",
             spark("slot_time_ms"), charts.ACCENT_ALT),
        _kpi("SOL price", usd(m.get("price_usd")), change_sub(market.get("change_24h_pct"), "24h"),
             spark("price_usd"), charts.ACCENT),
        _kpi("Market cap", usd(m.get("market_cap_usd")),
             f"rank #{num(market.get('market_cap_rank'))}", spark("market_cap_usd"), charts.ACCENT),
        _kpi("DeFi TVL", usd(m.get("tvl_usd")), change_sub(tvl.get("change_7d_pct"), "7d"),
             spark("tvl_usd"), charts.ACCENT_ALT),
        _kpi("DEX volume", usd(m.get("dex_volume_24h_usd")),
             change_sub(dex.get("change_1d_pct"), "24h"), spark("dex_volume_24h_usd"), "#38bdf8"),
        _kpi("Chain fees 24h", usd(m.get("chain_fees_24h_usd")),
             change_sub(fees.get("change_1d_pct"), "24h"), spark("chain_fees_24h_usd"), "#f59e0b"),
        _kpi("Stablecoins", usd(m.get("stablecoin_total_usd")),
             f"{num((s.get('stablecoins') or {}).get('asset_count'))} assets",
             spark("stablecoin_total_usd"), "#38bdf8"),
        _kpi("Validators", num(m.get("validator_count")),
             f"{num(m.get('delinquent_count'))} delinquent", spark("validator_count"), charts.ACCENT),
        _kpi("Nakamoto coefficient", num(m.get("nakamoto_coefficient")),
             ">33% of stake", spark("nakamoto_coefficient"), charts.ACCENT_ALT),
        _kpi("Delinquent stake", pct(m.get("delinquent_stake_pct"), 3), "of total stake",
             spark("delinquent_stake_pct"), "#fb5f6d"),
        _kpi("Median tx fee", f"{num(m.get('median_tx_fee_lamports'))}",
             f"lamports · {usd(m.get('median_tx_fee_usd'), 6)}",
             spark("median_tx_fee_lamports"), "#f59e0b"),
        _kpi("Tokenised RWA", usd(m.get("rwa_tvl_usd")),
             f"equities {usd(m.get('tokenized_equity_tvl_usd'))}", spark("rwa_tvl_usd"), charts.ACCENT),
        _kpi("Staking ratio", pct(m.get("staking_ratio_pct"), 1),
             f"{sol(v.get('total_stake_sol'))} staked", spark("total_stake_sol"), charts.ACCENT_ALT),
    ]
    return f'<div class="kpis">{"".join(tiles)}</div>'


def _payload(snapshot: dict[str, Any]) -> str:
    """Compact JSON embedded for the client-side validator table."""
    validators = (snapshot.get("sections", {}).get("validators") or {}).get("validators") or []
    return json.dumps({
        "generated_at": snapshot.get("generated_at"),
        "validators": [{
            "r": r["rank"], "v": r["vote_pubkey"], "n": r.get("node_pubkey") or "",
            "s": round(r["stake_sol"], 2), "p": round(r["stake_pct"], 5),
            "c": r.get("commission") if r.get("commission") is not None else 0,
            "d": 1 if r["delinquent"] else 0,
        } for r in validators],
    }, separators=(",", ":"))


def render(snapshot: dict[str, Any]) -> str:
    """Build the complete dashboard document."""
    hist = snapshot.get("_trend_history", [])
    counts = snapshot.get("anomaly_detection", {}).get("counts", {})
    summary = snapshot.get("source_summary", {})
    m = snapshot.get("metrics", {})

    severity_class = "crit" if counts.get("critical") else ("warn" if counts.get("warning") else "ok")
    nav = "".join(f'<a href="#{a}">{esc(t)}</a>' for a, t in SECTIONS)

    chips = (
        f'<div class="chips">'
        f'<span class="chip"><span class="pulse-dot"></span>generated <b class="age">just now</b></span>'
        f'<span class="chip">UTC <b>{esc(snapshot.get("generated_at"))}</b></span>'
        f'<span class="chip {severity_class}">alerts <b>{counts.get("total", 0)}</b></span>'
        f'<span class="chip">sources <b>{summary.get("ok")}/{summary.get("total")}</b> live</span>'
        f'<span class="chip">history <b>{snapshot.get("history", {}).get("records", 0)}</b> runs</span>'
        f'<span class="chip">epoch <b>{num(m.get("epoch"))}</b> · {pct(m.get("epoch_progress_pct"), 1)}</span>'
        f'<span class="chip">built in <b>{num(snapshot.get("runtime_seconds"), 1)}s</b></span>'
        f'<span class="chip">stdlib <b>only</b></span>'
        f'</div>'
    )

    body = "".join([
        _section("alerts", "01", "Alerts", "Anything the detectors flagged this run.",
                 _alerts_section(snapshot)),
        _section("network", "02", "Network performance",
                 "Throughput, slot time, epoch position and statistics parsed from raw blocks.",
                 _network_section(snapshot, hist)),
        _section("validators", "03", "Validators and decentralisation",
                 "Stake concentration, delinquency, commissions and client diversity.",
                 _validators_section(snapshot)),
        _section("economy", "04", "Economy",
                 "Price, supply, value locked, trading volume, fees and stablecoins.",
                 _economy_section(snapshot, hist)),
        _section("growth", "05", "Ecosystem growth",
                 "Tokenised assets, wallet activity and the token and program landscape.",
                 _growth_section(snapshot)),
        _section("upgrades", "06", "Upgrades, governance and news",
                 "Protocol proposals, client releases, incidents and the ecosystem feed.",
                 _upgrades_section(snapshot)),
        _section("sources", "07", "Data sources and freshness",
                 "Every source, its latency, and the exact error when one fails.",
                 _sources_section(snapshot)),
        _section("methodology", "08", "Methodology",
                 "How the numbers are produced and what they do not claim.",
                 _methodology_section(snapshot)),
    ])

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Solana Pulse — state of the Solana ecosystem</title>
<meta name="description" content="Auto-updating report on the state of the Solana ecosystem: network
performance, validators, economy, growth, upgrades and anomaly alerts. Built from public keyless
sources with the Python standard library only.">
<meta name="color-scheme" content="dark">
<meta property="og:title" content="Solana Pulse">
<meta property="og:description" content="Auto-updating state of the Solana ecosystem, with anomaly detection.">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='8' fill='%239945FF'/><path d='M7 21h4l3-10 4 14 3-8h4' stroke='%2314F195' stroke-width='2.4' fill='none' stroke-linecap='round' stroke-linejoin='round'/></svg>">
<style>{CSS}</style>
</head>
<body>
<header class="top"><div class="top-inner">
  <div class="brand"><span class="mark">◈</span>Solana&nbsp;Pulse</div>
  <div class="top-meta"><span class="pulse-dot"></span><span class="age">just now</span></div>
  <nav class="jump">{nav}</nav>
</div></header>
<div class="wrap">
  <div class="hero">
    <h1>The state of the <span>Solana ecosystem</span>, refreshed automatically.</h1>
    <p>Every number below was collected from public, keyless sources by a Python program with no
    third-party dependencies — Solana JSON-RPC, raw block parsing, DefiLlama, CoinGecko, GitHub and
    public RSS feeds — then checked against its own history for anomalies.</p>
    {chips}
  </div>
  {_kpi_strip(snapshot, hist)}
  {body}
  <footer>
    <span>Solana Pulse {esc(snapshot.get("generator", {}).get("version"))} · generated
      {esc(snapshot.get("generated_at"))} · Python {esc(snapshot.get("generator", {}).get("python"))},
      standard library only · MIT licence</span>
    <span><a href="report.md">Markdown report</a> · <a href="report.json">JSON</a> ·
      <a href="latest.json">latest.json</a> ·
      <a href="https://github.com/tradingstation111/solana-pulse">Source</a></span>
  </footer>
</div>
<script type="application/json" id="pulse-data">{_payload(snapshot)}</script>
<script>{SCRIPT}</script>
</body>
</html>
"""


def write(snapshot: dict[str, Any], out_dir: str) -> str:
    """Write ``index.html`` into ``out_dir`` and return the path."""
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "index.html")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(render(snapshot))
    return path
