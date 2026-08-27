"""Human-readable Markdown report.

Ordered the way someone actually reads a status report: what is wrong first,
then the headline numbers, then each domain in detail, then the provenance and
method that let a reader check the work.
"""

from __future__ import annotations

import os
from typing import Any

from render.fmt import DASH, ago, num, pct, short_date, sol, truncate, usd

SEVERITY_MARK = {"critical": "🔴 CRITICAL", "warning": "🟠 WARNING", "info": "🔵 INFO"}


def _table(headers: list[str], rows: list[list[str]]) -> list[str]:
    """Render a GitHub-flavoured Markdown table."""
    if not rows:
        return ["_No rows available._", ""]
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    out.append("")
    return out


def _degraded(snapshot: dict[str, Any], *keys: str) -> str | None:
    """Return a warning line if any of the named sections failed to collect."""
    missing = [k for k in keys if k not in snapshot.get("sections", {})]
    if not missing:
        return None
    errors = {
        s["name"]: s["error"] for s in snapshot.get("sources", [])
        if not s["ok"]
    }
    detail = "; ".join(f"`{k}`" for k in missing)
    reasons = "; ".join(f"{n} — {e}" for n, e in errors.items()) or "reason not recorded"
    return f"> ⚠️ **Source unavailable:** {detail}. This section is incomplete. Reported errors: {reasons}\n"


def render(snapshot: dict[str, Any]) -> str:
    """Produce the complete Markdown report as a string."""
    m = snapshot.get("metrics", {})
    s = snapshot.get("sections", {})
    lines: list[str] = []
    add = lines.append

    generated = snapshot.get("generated_at")
    add("# Solana Pulse — State of the Solana Ecosystem")
    add("")
    add(f"**Generated:** {generated} · **Run time:** {snapshot.get('runtime_seconds')}s · "
        f"**History depth:** {snapshot.get('history', {}).get('records', 0)} runs · "
        f"**Sources:** {snapshot.get('source_summary', {}).get('ok')}/"
        f"{snapshot.get('source_summary', {}).get('total')} live")
    add("")
    add("Automatically generated from public, keyless data sources using the Python "
        "standard library only. No API keys, no third-party packages.")
    add("")

    # --- Alerts ------------------------------------------------------------
    detection = snapshot.get("anomaly_detection", {})
    counts = detection.get("counts", {})
    add("## 1. Alerts")
    add("")
    if not detection.get("baseline_ready"):
        add(f"> Baseline building: {detection.get('baseline_runs', 0)} of "
            f"{detection.get('method', {}).get('min_points')} runs collected. Statistical "
            "detection activates once enough history exists; threshold and cross-source "
            "rules are already active.")
        add("")
    alerts = snapshot.get("alerts", [])
    if not alerts:
        add("**No anomalies detected.** All monitored metrics are within their expected ranges.")
        add("")
    else:
        add(f"**{counts.get('total', 0)} active** — {counts.get('critical', 0)} critical, "
            f"{counts.get('warning', 0)} warning, {counts.get('info', 0)} informational.")
        add("")
        for alert in alerts:
            add(f"- {SEVERITY_MARK.get(alert['severity'], alert['severity'])} "
                f"**{alert['title']}** ({alert['detector']}) — {alert['detail']}")
        add("")

    # --- Headline ----------------------------------------------------------
    add("## 2. At a glance")
    add("")
    rows = [
        ["Throughput", num(m.get("tps"), 0, " TPS"), f"non-vote {num(m.get('non_vote_tps'), 0, ' TPS')}"],
        ["Slot time", num(m.get("slot_time_ms"), 0, " ms"), "~400 ms target"],
        ["Epoch", num(m.get("epoch")), f"{pct(m.get('epoch_progress_pct'), 1)} complete"],
        ["Validators", num(m.get("validator_count")), f"{num(m.get('delinquent_count'))} delinquent"],
        ["Nakamoto coefficient", num(m.get("nakamoto_coefficient")), "validators controlling >33% of stake"],
        ["SOL price", usd(m.get("price_usd")), pct(m.get("change_24h_pct"), 2, True) + " 24h"],
        ["Market cap", usd(m.get("market_cap_usd")), f"rank #{num((s.get('market') or {}).get('market_cap_rank'))}"],
        ["DeFi TVL", usd(m.get("tvl_usd")), pct((s.get("tvl") or {}).get("change_7d_pct"), 2, True) + " 7d"],
        ["DEX volume 24h", usd(m.get("dex_volume_24h_usd")), pct((s.get("dex") or {}).get("change_1d_pct"), 2, True)],
        ["Chain fees 24h (REV)", usd(m.get("chain_fees_24h_usd")), pct((s.get("fees") or {}).get("change_1d_pct"), 2, True)],
        ["Stablecoins on Solana", usd(m.get("stablecoin_total_usd")), f"{num((s.get('stablecoins') or {}).get('asset_count'))} assets"],
        ["Tokenised RWA", usd(m.get("rwa_tvl_usd")), f"equities {usd(m.get('tokenized_equity_tvl_usd'))}"],
        ["Median transaction fee", f"{num(m.get('median_tx_fee_lamports'))} lamports", usd(m.get("median_tx_fee_usd"), 6)],
        ["Staking ratio", pct(m.get("staking_ratio_pct"), 1), f"{sol(m.get('total_stake_sol'))} staked"],
    ]
    lines.extend(_table(["Metric", "Value", "Context"], rows))

    # --- Network -----------------------------------------------------------
    add("## 3. Network performance")
    add("")
    warn = _degraded(snapshot, "performance", "cluster")
    if warn:
        add(warn)
    cluster = s.get("cluster") or {}
    perf = s.get("performance") or {}
    add(f"Cluster health is **{cluster.get('health', DASH)}** on `{cluster.get('endpoint', DASH)}`, "
        f"running solana-core **{cluster.get('solana_core', DASH)}** (feature set "
        f"{num(cluster.get('feature_set'))}).")
    add("")
    lines.extend(_table(
        ["Metric", "Current", f"Mean ({num(perf.get('window_minutes'))} samples)"],
        [
            ["Transactions per second", num(perf.get("tps_current"), 1), num(perf.get("tps_mean"), 1)],
            ["Non-vote TPS", num(perf.get("non_vote_tps_current"), 1), num(perf.get("non_vote_tps_mean"), 1)],
            ["Slot time (ms)", num(perf.get("slot_time_ms_current"), 1), num(perf.get("slot_time_ms_mean"), 1)],
            ["Peak TPS in window", num(perf.get("tps_max"), 1), DASH],
            ["Absolute slot", num(cluster.get("absolute_slot")), DASH],
            ["Block height", num(cluster.get("block_height")), DASH],
            ["Lifetime transactions", num(cluster.get("transaction_count")), DASH],
            ["Slots left in epoch", num(cluster.get("epoch_slots_remaining")), DASH],
        ],
    ))

    sample = s.get("blocks")
    add("### 3.1 Direct block sampling")
    add("")
    if not sample:
        add(_degraded(snapshot, "blocks") or "> ⚠️ Block sampling unavailable this run.")
        add("")
    else:
        add(f"{sample['blocks_sampled']} finalised blocks were downloaded in full and parsed "
            f"locally, spanning {num(sample.get('sample_span_seconds'))} seconds of chain time. "
            "These figures are computed from raw block contents, not from any aggregator.")
        add("")
        lines.extend(_table(["Measurement", "Value"], [
            ["Median user transaction fee", f"{num(sample.get('median_tx_fee_lamports'))} lamports "
                                            f"({usd(m.get('median_tx_fee_usd'), 6)})"],
            ["90th percentile fee", f"{num(sample.get('p90_tx_fee_lamports'))} lamports"],
            ["Median priority fee", f"{num(sample.get('median_priority_fee_lamports'))} lamports"],
            ["Priority fees as share of fees paid", pct(sample.get("priority_fee_share_pct"), 1)],
            ["On-chain transaction failure rate", pct(sample.get("tx_failure_rate_pct"), 1)],
            ["Vote transactions as share of all", pct(sample.get("vote_tx_share_pct"), 1)],
            ["Average transactions per block", num(sample.get("avg_txs_per_block"), 0)],
            ["Average unique fee payers per block", num(sample.get("avg_unique_payers_per_block"), 0)],
            ["Unique fee payers across the sample", num(sample.get("unique_payers_in_sample"))],
            ["Wallets active in sampling window (capture-recapture estimate)",
             num(sample.get("window_active_wallet_estimate"), 0)],
            ["New-wallet discovery rate", num(sample.get("new_payer_discovery_rate_per_s"), 2, " /s")],
        ]))

    # --- Validators --------------------------------------------------------
    add("## 4. Validators and decentralisation")
    add("")
    v = s.get("validators")
    if not v:
        add(_degraded(snapshot, "validators") or "")
    else:
        add(f"**{num(v.get('active_count'))} active** validators and "
            f"**{num(v.get('delinquent_count'))} delinquent**, securing "
            f"{sol(v.get('total_stake_sol'))} of stake "
            f"({usd(m.get('staked_value_usd'))} at the current price). Delinquent stake is "
            f"{pct(v.get('delinquent_stake_pct'), 3)} of the total.")
        add("")
        lines.extend(_table(["Concentration measure", "Value"], [
            ["Nakamoto coefficient (>33% of stake)", num(v.get("nakamoto_coefficient"))],
            ["Largest validator share", pct(v.get("top1_stake_pct"), 2)],
            ["Top 10 share", pct(v.get("top10_stake_pct"), 2)],
            ["Top 20 share", pct(v.get("top20_stake_pct"), 2)],
            ["Top 100 share", pct(v.get("top100_stake_pct"), 2)],
            ["Median validator stake", sol(v.get("median_stake_sol"))],
            ["Median commission", pct(v.get("median_commission"), 0)],
            ["Zero-commission validators", num(v.get("zero_commission_count"))],
        ]))
        add("**Top 15 validators by activated stake**")
        add("")
        lines.extend(_table(
            ["#", "Vote account", "Stake", "Share", "Commission", "Status"],
            [[
                str(r["rank"]), f"`{truncate(r['vote_pubkey'], 20)}`", sol(r["stake_sol"]),
                pct(r["stake_pct"], 3), pct(r["commission"], 0),
                "delinquent" if r["delinquent"] else "active",
            ] for r in (v.get("validators") or [])[:15]],
        ))
        delinquent_rows = v.get("top_delinquent") or []
        add("**Largest delinquent validators**")
        add("")
        if delinquent_rows:
            lines.extend(_table(["Vote account", "Stake", "Share", "Last vote"],
                                [[f"`{truncate(r['vote_pubkey'], 20)}`", sol(r["stake_sol"]),
                                  pct(r["stake_pct"], 4), num(r.get("last_vote"))]
                                 for r in delinquent_rows[:10]]))
        else:
            add("_No delinquent validators are currently reported._")
            add("")
        add("**Commission distribution**")
        add("")
        lines.extend(_table(["Commission band", "Validators"],
                            [[k, num(val)] for k, val in (v.get("commission_buckets") or {}).items()]))

    nodes = s.get("cluster_nodes")
    add("### 4.1 Validator client diversity")
    add("")
    if not nodes:
        add(_degraded(snapshot, "cluster_nodes") or "")
    else:
        add(f"{num(nodes.get('gossip_node_count'))} nodes are visible over gossip across "
            f"{num(nodes.get('distinct_versions'))} distinct software versions. "
            f"The dominant client is **{nodes.get('dominant_client')}** at "
            f"{pct(nodes.get('dominant_client_pct'), 1)} of nodes.")
        add("")
        lines.extend(_table(["Client", "Nodes", "Share"],
                            [[r["client"], num(r["nodes"]), pct(r["share_pct"], 1)]
                             for r in nodes.get("clients") or []]))

    # --- Economy -----------------------------------------------------------
    add("## 5. Economy")
    add("")
    market = s.get("market")
    if market:
        add(f"SOL trades at **{usd(market.get('price_usd'))}** — "
            f"{pct(market.get('change_1h_pct'), 2, True)} in 1h, "
            f"{pct(market.get('change_24h_pct'), 2, True)} in 24h, "
            f"{pct(market.get('change_7d_pct'), 2, True)} in 7d, "
            f"{pct(market.get('change_30d_pct'), 2, True)} in 30d. "
            f"It sits {pct(market.get('ath_change_pct'), 1)} from its all-time high of "
            f"{usd(market.get('ath_usd'))} set on {short_date(market.get('ath_date'))}.")
        add("")
        lines.extend(_table(["Market metric", "Value"], [
            ["Market capitalisation", f"{usd(market.get('market_cap_usd'))} (rank #{num(market.get('market_cap_rank'))})"],
            ["Fully diluted valuation", usd(market.get("fully_diluted_valuation_usd"))],
            ["24h volume", usd(market.get("volume_24h_usd"))],
            ["Volume / market cap", pct(market.get("volume_to_mcap_pct"), 2)],
            ["24h range", f"{usd(market.get('low_24h'))} – {usd(market.get('high_24h'))}"],
            ["Market cap / TVL", num(m.get("mcap_to_tvl"), 2)],
            ["Annualised fees / market cap", pct(m.get("annualised_fee_to_mcap_pct"), 2)],
        ]))
    else:
        add(_degraded(snapshot, "market") or "")

    supply = s.get("supply")
    if supply:
        add("**Supply and inflation**")
        add("")
        lines.extend(_table(["Supply metric", "Value"], [
            ["Total supply", sol(supply.get("total_supply_sol"))],
            ["Circulating supply", f"{sol(supply.get('circulating_supply_sol'))} "
                                   f"({pct(supply.get('circulating_pct'), 1)})"],
            ["Non-circulating", sol(supply.get("non_circulating_sol"))],
            ["Current inflation rate", pct(supply.get("inflation_total_pct"), 3)],
            ["Staking ratio (stake / circulating)", pct(m.get("staking_ratio_pct"), 1)],
        ]))

    tvl = s.get("tvl")
    if tvl:
        add("**Total value locked**")
        add("")
        add(f"Solana holds {usd(tvl.get('tvl_usd'))} in DeFi TVL, ranking **#{num(tvl.get('tvl_rank'))}** "
            f"of {num(tvl.get('chain_count'))} tracked chains and "
            f"{pct(tvl.get('share_of_all_chains_pct'), 2)} of all on-chain TVL. "
            f"Change: {pct(tvl.get('change_1d_pct'), 2, True)} (24h), "
            f"{pct(tvl.get('change_7d_pct'), 2, True)} (7d), "
            f"{pct(tvl.get('change_30d_pct'), 2, True)} (30d).")
        add("")

    protocols = s.get("protocols")
    if protocols:
        add("**Top protocols by TVL on Solana**")
        add("")
        add(f"_Centralised-exchange wallets and bridge contracts are excluded from these figures "
            f"({', '.join(protocols.get('excluded_categories', []))}), because they hold assets on "
            f"Solana without being Solana DeFi._")
        add("")
        lines.extend(_table(["#", "Protocol", "Category", "TVL", "24h", "7d"],
                            [[str(i), r["name"], r["category"], usd(r["tvl_usd"]),
                              pct(r.get("change_1d_pct"), 1, True), pct(r.get("change_7d_pct"), 1, True)]
                             for i, r in enumerate(protocols.get("top_protocols", [])[:15], 1)]))
        add("**TVL by category**")
        add("")
        lines.extend(_table(["Category", "TVL"],
                            [[r["category"], usd(r["tvl_usd"])] for r in protocols.get("categories", [])[:10]]))

    dex = s.get("dex")
    if dex:
        add("**DEX volume**")
        add("")
        add(f"{usd(dex.get('total_24h_usd'))} traded in 24h across {num(dex.get('protocol_count'))} "
            f"venues ({pct(dex.get('change_1d_pct'), 1, True)} day over day, "
            f"{pct(dex.get('change_7d_pct'), 1, True)} week over week). "
            f"7-day total {usd(dex.get('total_7d_usd'))}, 30-day total {usd(dex.get('total_30d_usd'))}.")
        add("")
        lines.extend(_table(["Venue", "24h volume", "7d volume", "24h change"],
                            [[r["name"], usd(r["total_24h_usd"]), usd(r.get("total_7d_usd")),
                              pct(r.get("change_1d_pct"), 1, True)]
                             for r in dex.get("top_protocols", [])[:10]]))

    fees = s.get("fees")
    if fees:
        add("**Fees and Real Economic Value**")
        add("")
        add(f"{usd(fees.get('total_24h_usd'))} in fees were paid on Solana in the last 24h "
            f"({pct(fees.get('change_1d_pct'), 1, True)} day over day), "
            f"{usd(fees.get('total_7d_usd'))} over 7 days and {usd(fees.get('total_30d_usd'))} over 30 days. "
            f"Lifetime fees stand at {usd(fees.get('total_all_time_usd'))}.")
        add("")
        lines.extend(_table(["Fee-generating protocol", "24h fees", "7d fees"],
                            [[r["name"], usd(r["total_24h_usd"]), usd(r.get("total_7d_usd"))]
                             for r in fees.get("top_protocols", [])[:10]]))

    stables = s.get("stablecoins")
    if stables:
        add("**Stablecoins on Solana**")
        add("")
        add(f"{usd(stables.get('total_usd'))} across {num(stables.get('asset_count'))} assets; "
            f"the largest holds {pct(stables.get('top_share_pct'), 1)} of the float.")
        add("")
        lines.extend(_table(["Asset", "Circulating on Solana", "24h", "7d", "Peg type"],
                            [[f"{r['symbol']} ({r['name']})", usd(r["circulating_usd"]),
                              pct(r.get("change_1d_pct"), 2, True), pct(r.get("change_7d_pct"), 2, True),
                              r.get("peg_mechanism") or DASH]
                             for r in stables.get("assets", [])[:12]]))

    # --- Growth ------------------------------------------------------------
    add("## 6. Ecosystem growth")
    add("")
    if protocols:
        add(f"**Tokenised real-world assets:** {usd(protocols.get('rwa_tvl_usd'))} across "
            f"{num(len(protocols.get('rwa_protocols', [])))} tracked issuers, of which "
            f"{usd(protocols.get('tokenized_equity_tvl_usd'))} is tokenised equity exposure.")
        add("")
        lines.extend(_table(["RWA issuer", "Value on Solana", "24h"],
                            [[r["name"], usd(r["tvl_usd"]), pct(r.get("change_1d_pct"), 1, True)]
                             for r in protocols.get("rwa_protocols", [])[:10]]))
    if sample:
        add(f"**Wallet activity:** {num(sample.get('avg_unique_payers_per_block'), 0)} distinct fee "
            f"payers appeared in the average sampled block, and "
            f"{num(sample.get('unique_payers_in_sample'))} distinct wallets across the whole sample. "
            f"Projected user (non-vote) transactions per day at the current rate: "
            f"{num(m.get('projected_daily_user_txs'), 0)}.")
        add("")
    tokens = s.get("ecosystem_tokens")
    if tokens:
        add("**Largest Solana-ecosystem tokens by market cap**")
        add("")
        lines.extend(_table(["Token", "Price", "Market cap", "24h volume", "24h"],
                            [[f"{r['symbol']} ({r['name']})", usd(r["price_usd"], 4),
                              usd(r["market_cap_usd"]), usd(r["volume_24h_usd"]),
                              pct(r.get("change_24h_pct"), 1, True)]
                             for r in tokens[:12]]))
    accounts = s.get("accounts")
    if accounts:
        add("**Watched programs and accounts**")
        add("")
        lines.extend(_table(["Label", "Address", "Balance", "Sig. rate", "Failures in sample"],
                            [[r["label"], f"`{truncate(r['address'], 16)}`", sol(r.get("balance_sol"), 4),
                              num(r.get("sig_rate_per_min"), 1, "/min"), pct(r.get("failure_rate_pct"), 0)]
                             for r in accounts]))

    # --- Upgrades and news -------------------------------------------------
    add("## 7. Upgrades, governance and news")
    add("")
    simds = s.get("simds")
    if simds:
        add(f"**{num(simds.get('open_count'))} open SIMDs** (Solana Improvement Documents).")
        add("")
        if simds.get("highlighted"):
            add("_Proposals being tracked closely:_")
            add("")
            lines.extend(_table(["SIMD", "Title", "State", "Updated"],
                                [[f"#{r['number']}", f"[{truncate(r['title'], 90)}]({r['url']})",
                                  r["state"], short_date(r.get("updated_at"))]
                                 for r in simds["highlighted"][:8]]))
        add("_Recently merged:_")
        add("")
        lines.extend(_table(["PR", "Title", "Merged"],
                            [[f"#{r['number']}", f"[{truncate(r['title'], 90)}]({r['url']})",
                              short_date(r.get("merged_at"))]
                             for r in simds.get("recently_merged", [])[:8]]))
        add("_Open proposals, most recently updated:_")
        add("")
        lines.extend(_table(["PR", "Title", "Author", "Opened"],
                            [[f"#{r['number']}", f"[{truncate(r['title'], 80)}]({r['url']})",
                              r.get("author") or DASH, short_date(r.get("created_at"))]
                             for r in simds.get("open", [])[:10]]))
    releases = s.get("releases")
    if releases:
        add("**Validator client releases**")
        add("")
        rows = []
        for client in releases.get("clients", []):
            latest = client.get("latest_stable") or {}
            rows.append([client["client"], latest.get("tag") or DASH,
                         short_date(latest.get("published")),
                         f"[release notes]({latest.get('url')})" if latest.get("url") else DASH])
        lines.extend(_table(["Client", "Latest stable", "Published", "Link"], rows))
    status = s.get("status")
    if status:
        add(f"**Cluster status page:** {status.get('description', DASH)} "
            f"(indicator: `{status.get('indicator', DASH)}`, updated {short_date(status.get('updated_at'))}).")
        add("")
    newsdata = s.get("news")
    if newsdata:
        add("**Latest ecosystem news**")
        add("")
        for item in newsdata.get("items", [])[:12]:
            add(f"- **{short_date(item.get('published'))}** · _{item['source']}_ · "
                f"[{truncate(item['title'], 120)}]({item['link']})")
        add("")
        if newsdata.get("failed_feeds"):
            add(f"> Feeds unavailable this run: {'; '.join(newsdata['failed_feeds'])}")
            add("")
        add("_Social sentiment from X is deliberately omitted: there is no keyless, "
            "terms-compliant read path, and inventing it would be worse than leaving it out. "
            "Official accounts: "
            + ", ".join(f"[{a['handle']}]({a['url']})" for a in newsdata.get("x_accounts", []))
            + "._")
        add("")

    # --- Trends ------------------------------------------------------------
    add("## 8. Trend history")
    add("")
    hist = snapshot.get("_trend_history", [])
    add(f"This deployment has {len(hist)} recorded runs, the first at "
        f"{snapshot.get('history', {}).get('first_run')}. Every run appends one line to "
        f"`{snapshot.get('history', {}).get('path')}`; the anomaly detector reads it back as its baseline.")
    add("")
    if len(hist) >= 2:
        watched = [("tps", "TPS", 0), ("slot_time_ms", "Slot time (ms)", 0),
                   ("validator_count", "Validators", 0), ("delinquent_stake_pct", "Delinquent stake %", 3),
                   ("price_usd", "SOL price (USD)", 2), ("tvl_usd", "TVL (USD)", 0),
                   ("nakamoto_coefficient", "Nakamoto coefficient", 0)]
        rows = []
        for key, label, decimals in watched:
            values = [r[key] for r in hist if isinstance(r.get(key), (int, float))]
            if len(values) < 2:
                continue
            first, last = values[0], values[-1]
            change = (last - first) / first * 100 if first else None
            rows.append([label, num(first, decimals), num(last, decimals),
                         num(min(values), decimals), num(max(values), decimals),
                         pct(change, 2, True)])
        lines.extend(_table(["Metric", "First run", "Latest", "Min", "Max", "Change"], rows))

    # --- Sources -----------------------------------------------------------
    add("## 9. Data sources and freshness")
    add("")
    lines.extend(_table(["Source", "Status", "Latency", "Fetched", "Detail"],
                        [[src["name"], "🟢 live" if src["ok"] else "🔴 unavailable",
                          f"{src['elapsed_ms']} ms", ago(src["fetched_at"]),
                          truncate(src.get("error") or "; ".join(src.get("notes") or []) or "—", 90)]
                         for src in snapshot.get("sources", [])]))

    # --- Methodology -------------------------------------------------------
    method = detection.get("method", {})
    add("## 10. Methodology")
    add("")
    add("**Collection.** Each source is fetched independently and wrapped so that a failure "
        "downgrades exactly one section rather than the run. Solana RPC calls fail over across "
        "public endpoints; every other source is a public HTTP API or RSS/Atom feed. No API key "
        "is used anywhere and the only dependency is the Python standard library.")
    add("")
    add("**Anomaly detection.** Three detectors run on every report:")
    add("")
    add(f"1. *Statistical* — modified z-score `{method.get('statistical')}` over the last "
        f"{method.get('window_runs')} runs. Median and median absolute deviation are used instead "
        f"of mean and standard deviation so that one earlier spike cannot mask the next one. "
        f"|z| ≥ {method.get('warn_z')} raises a warning, |z| ≥ {method.get('critical_z')} is critical. "
        f"Metrics are direction-aware: a rising Nakamoto coefficient never alerts. Detection stays "
        f"quiet until {method.get('min_points')} runs of history exist.")
    add(f"2. *Threshold rules* — fixed conditions that are bad regardless of history "
        f"(unhealthy RPC, slot time above 600 ms, delinquent stake above 2%, failure rate above 65%, "
        f"client monoculture above 85%, stablecoin depeg beyond 2%).")
    add("3. *Cross-source correlation* — signals that exist only because several sources are held "
        "together: TVL diverging from price, the fee-to-DEX-volume ratio shifting, throughput and "
        "failure rate rising together, stablecoin share of TVL rotating.")
    add("")
    add("**Block sampling.** Median fees, failure rates and wallet counts are computed from raw "
        "blocks downloaded over RPC and parsed locally, so those figures do not depend on any "
        "aggregator. The active-wallet estimate uses Chapman's capture-recapture estimator over two "
        "disjoint halves of the sample; because heavy automated wallets appear in every block, that "
        "figure is an order-of-magnitude indication for the sampling window, not a daily user count.")
    add("")
    add("**Limits.** Aggregated economic figures (TVL, DEX volume, fees, stablecoin float) carry "
        "their providers' methodologies and revisions. Point-in-time RPC readings reflect the "
        "endpoint that answered. X/Twitter sentiment is not collected.")
    add("")
    add("---")
    add("")
    add(f"Solana Pulse {snapshot.get('generator', {}).get('version')} · "
        f"Python {snapshot.get('generator', {}).get('python')} · "
        f"{snapshot.get('generator', {}).get('dependencies')} · MIT licence")
    return "\n".join(line for line in lines if line is not None) + "\n"


def write(snapshot: dict[str, Any], out_dir: str) -> str:
    """Write ``report.md`` into ``out_dir`` and return the path."""
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "report.md")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(render(snapshot))
    return path
