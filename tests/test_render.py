"""Tests for the renderers and chart primitives.

These build a synthetic snapshot - including a deliberately failed source - and
assert that all three outputs are produced, that a failure is visibly reported
rather than silently dropped, and that no chart helper raises on degenerate
input.
"""

from __future__ import annotations

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from render import charts, fmt, html as html_renderer, jsonout, markdown as md_renderer  # noqa: E402


def make_snapshot() -> dict:
    """A snapshot with one live section and one failed source."""
    return {
        "schema_version": "1.0",
        "generated_at": "2026-08-26T12:00:00Z",
        "runtime_seconds": 12.3,
        "generator": {"name": "Solana Pulse", "version": "1.0.0", "python": "3.12.3",
                      "dependencies": "Python standard library only",
                      "rpc_endpoint": "https://api.mainnet-beta.solana.com", "rpc_calls": 14},
        "metrics": {
            "tps": 4100.0, "non_vote_tps": 2300.0, "slot_time_ms": 380.0, "epoch": 1023,
            "epoch_progress_pct": 42.5, "validator_count": 697, "delinquent_count": 12,
            "delinquent_stake_pct": 0.04, "nakamoto_coefficient": 18, "price_usd": 101.5,
            "market_cap_usd": 5.9e10, "tvl_usd": 5.6e9, "dex_volume_24h_usd": 2.4e9,
            "chain_fees_24h_usd": 1.3e7, "stablecoin_total_usd": 1.6e10,
            "median_tx_fee_lamports": 5300, "median_tx_fee_usd": 0.00054,
            "rwa_tvl_usd": 2.0e9, "tokenized_equity_tvl_usd": 4.5e8, "staking_ratio_pct": 74.8,
        },
        "sections": {
            "cluster": {"health": "ok", "endpoint": "https://api.mainnet-beta.solana.com",
                        "solana_core": "4.2.0", "epoch": 1023, "epoch_progress_pct": 42.5,
                        "absolute_slot": 441_995_000, "block_height": 420_000_000,
                        "slot_index": 1, "slots_in_epoch": 432000, "epoch_slots_remaining": 431999,
                        "transaction_count": 542_000_000_000, "feature_set": 565236538},
            "performance": {"samples": [{"tps": 4000 + i, "slot_time_ms": 380, "non_vote_tps": 2200}
                                        for i in range(10)],
                            "tps_current": 4100.0, "tps_mean": 4050.0, "tps_max": 4200.0,
                            "slot_time_ms_current": 380.0, "slot_time_ms_mean": 381.0,
                            "non_vote_tps_current": 2300.0, "non_vote_tps_mean": 2250.0,
                            "window_minutes": 10},
            "validators": {
                "validator_count": 2, "active_count": 1, "delinquent_count": 1,
                "total_stake_sol": 1000.0, "delinquent_stake_sol": 10.0,
                "delinquent_stake_pct": 1.0, "nakamoto_coefficient": 1,
                "top1_stake_pct": 99.0, "top10_stake_pct": 100.0, "top20_stake_pct": 100.0,
                "top100_stake_pct": 100.0, "median_stake_sol": 500.0, "median_commission": 5,
                "zero_commission_count": 1, "commission_buckets": {"0%": 1, "1-5%": 1},
                "validators": [
                    {"rank": 1, "vote_pubkey": "Vote1111", "node_pubkey": "Node1111",
                     "stake_sol": 990.0, "stake_pct": 99.0, "commission": 0, "delinquent": False,
                     "last_vote": 1, "root_slot": 1, "epoch_credits": 10},
                    {"rank": 2, "vote_pubkey": "Vote2222", "node_pubkey": "Node2222",
                     "stake_sol": 10.0, "stake_pct": 1.0, "commission": 5, "delinquent": True,
                     "last_vote": 1, "root_slot": 1, "epoch_credits": 0},
                ],
                "top_delinquent": [{"vote_pubkey": "Vote2222", "stake_sol": 10.0,
                                    "stake_pct": 1.0, "last_vote": 1}],
            },
            "blocks": {"blocks_sampled": 2, "sample_span_seconds": 120,
                       "median_tx_fee_lamports": 5300, "p90_tx_fee_lamports": 25000,
                       "median_priority_fee_lamports": 300, "priority_fee_share_pct": 70.0,
                       "tx_failure_rate_pct": 44.0, "vote_tx_share_pct": 40.0,
                       "avg_txs_per_block": 1800, "avg_unique_payers_per_block": 330,
                       "unique_payers_in_sample": 600, "payer_recapture_overlap": 100,
                       "window_active_wallet_estimate": 900.0,
                       "new_payer_discovery_rate_per_s": 4.5,
                       "fees_paid_sol_in_sample": 0.2,
                       "blocks": [{"slot": 1, "tx_count": 10, "user_tx_count": 6,
                                   "unique_fee_payers": 5, "failure_rate_pct": 33.0,
                                   "median_user_fee_lamports": 5300}]},
            "status": {"indicator": "none", "description": "All Systems Operational",
                       "components": [], "degraded_components": [], "incidents": []},
            "news": {"items": [{"source": "Solana News", "title": "A post",
                                "link": "https://solana.com/news/a",
                                "published": "2026-08-25T00:00:00Z", "summary": "Body"}],
                     "feed_count": 5, "failed_feeds": [],
                     "x_accounts": [{"handle": "@solana", "url": "https://x.com/solana"}]},
            "simds": {"open_count": 1, "open": [{"number": 1, "title": "A proposal", "url": "u",
                                                 "author": "x", "created_at": "2026-08-01T00:00:00Z",
                                                 "updated_at": "2026-08-02T00:00:00Z",
                                                 "state": "open", "simd": 1, "highlight": False}],
                      "recently_merged": [], "highlighted": [], "highlight_keywords": ["alpenglow"]},
        },
        "alerts": [{"severity": "warning", "metric": "tps", "title": "TPS drop",
                    "detail": "Throughput fell.", "value": 100.0, "baseline": 4000.0,
                    "z_score": -6.2, "detector": "robust-z", "tags": ["statistical"]}],
        "anomaly_detection": {"counts": {"critical": 0, "warning": 1, "info": 0, "total": 1},
                              "baseline_runs": 9, "metrics_scored": 5,
                              "metrics_building_baseline": 0, "baseline_ready": True,
                              "scores": {}, "method": {"statistical": "modified z", "window_runs": 96,
                                                       "warn_z": 3.5, "critical_z": 5.0,
                                                       "min_points": 5}},
        "sources": [
            {"name": "Solana RPC: cluster", "url": "https://api.mainnet-beta.solana.com",
             "ok": True, "error": None, "elapsed_ms": 120,
             "fetched_at": "2026-08-26T12:00:00Z", "notes": []},
            {"name": "CoinGecko: SOL market", "url": "https://api.coingecko.com/x", "ok": False,
             "error": "FetchError: HTTP 429 Too Many Requests", "elapsed_ms": 900,
             "fetched_at": "2026-08-26T12:00:00Z", "notes": []},
        ],
        "source_summary": {"total": 2, "ok": 1, "degraded": ["CoinGecko: SOL market"]},
        "history": {"records": 9, "path": "data/history.jsonl", "first_run": "2026-08-26T04:00:00Z"},
        "_trend_history": [{"ts": f"2026-08-26T0{i}:00:00Z", "tps": 4000 + i * 10,
                            "price_usd": 100 + i, "tvl_usd": 5.6e9} for i in range(9)],
    }


class HtmlRenderTests(unittest.TestCase):
    """The dashboard must be self-contained and honest about failures."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.doc = html_renderer.render(make_snapshot())

    def test_is_a_complete_document(self) -> None:
        self.assertTrue(self.doc.startswith("<!DOCTYPE html>"))
        self.assertTrue(self.doc.rstrip().endswith("</html>"))

    def test_has_no_external_resource_references(self) -> None:
        """No CDN, no remote font, no remote script: it must work offline."""
        for pattern in ('<script src=', '<link rel="stylesheet"', "@import", "cdn."):
            self.assertNotIn(pattern, self.doc, pattern)

    def test_failed_source_is_shown_with_its_error(self) -> None:
        self.assertIn("CoinGecko: SOL market", self.doc)
        self.assertIn("HTTP 429 Too Many Requests", self.doc)

    def test_alert_is_rendered_with_severity(self) -> None:
        self.assertIn("TPS drop", self.doc)
        self.assertIn('class="alert warning"', self.doc)

    def test_every_section_anchor_exists(self) -> None:
        for anchor, _ in html_renderer.SECTIONS:
            self.assertIn(f'id="{anchor}"', self.doc)

    def test_validator_payload_is_valid_json(self) -> None:
        start = self.doc.index('id="pulse-data">') + len('id="pulse-data">')
        payload = json.loads(self.doc[start:self.doc.index("</script>", start)])
        self.assertEqual(len(payload["validators"]), 2)
        self.assertEqual(payload["validators"][0]["v"], "Vote1111")

    def test_content_is_escaped(self) -> None:
        snapshot = make_snapshot()
        snapshot["alerts"][0]["title"] = "<img src=x onerror=alert(1)>"
        self.assertNotIn("<img src=x", html_renderer.render(snapshot))


class MarkdownRenderTests(unittest.TestCase):
    """The Markdown report must carry the same facts as the dashboard."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.text = md_renderer.render(make_snapshot())

    def test_all_sections_present(self) -> None:
        for heading in ("## 1. Alerts", "## 2. At a glance", "## 3. Network performance",
                        "## 4. Validators", "## 5. Economy", "## 6. Ecosystem growth",
                        "## 7. Upgrades", "## 8. Trend history", "## 9. Data sources",
                        "## 10. Methodology"):
            self.assertIn(heading, self.text)

    def test_degraded_source_is_named(self) -> None:
        self.assertIn("CoinGecko: SOL market", self.text)
        self.assertIn("unavailable", self.text)

    def test_tables_are_well_formed(self) -> None:
        for line in self.text.splitlines():
            if line.startswith("|") and not line.startswith("|---"):
                self.assertTrue(line.endswith("|"), line)


class JsonRenderTests(unittest.TestCase):
    """JSON output must be serialisable and free of private keys."""

    def test_latest_summary_shape(self) -> None:
        latest = jsonout.build_latest(make_snapshot())
        self.assertEqual(latest["status"], "warning")
        self.assertEqual(latest["alerts"]["total"], 1)
        self.assertIn("tps", latest["metrics"])

    def test_private_keys_are_stripped(self) -> None:
        cleaned = jsonout._clean(make_snapshot())
        self.assertNotIn("_trend_history", cleaned)
        self.assertEqual(json.loads(json.dumps(cleaned))["schema_version"], "1.0")

    def test_status_is_critical_when_a_critical_alert_exists(self) -> None:
        snapshot = make_snapshot()
        snapshot["anomaly_detection"]["counts"]["critical"] = 1
        self.assertEqual(jsonout.build_latest(snapshot)["status"], "critical")


class ChartTests(unittest.TestCase):
    """Chart helpers must never raise, whatever they are handed."""

    def test_sparkline_with_too_few_points_degrades_gracefully(self) -> None:
        self.assertIn("collecting history", charts.sparkline([1]))

    def test_sparkline_with_identical_values(self) -> None:
        self.assertIn("<polyline", charts.sparkline([5, 5, 5, 5]))

    def test_area_chart_with_no_points(self) -> None:
        self.assertIn("chart-empty", charts.area_chart([], label="x"))

    def test_area_chart_custom_axis_labels_are_escaped(self) -> None:
        svg = charts.area_chart([[0, 1], [1, 2]], x_labels=("<a>", "now"))
        self.assertIn("&lt;a&gt;", svg)

    def test_donut_and_bars_with_empty_input(self) -> None:
        self.assertIn("chart-empty", charts.donut([]))
        self.assertIn("chart-empty", charts.bar_chart([]))

    def test_gauge_clamps_out_of_range_values(self) -> None:
        self.assertIn("width:100.00%", charts.gauge(180))
        self.assertIn("width:0.00%", charts.gauge(-4))

    def test_bar_labels_are_escaped(self) -> None:
        self.assertIn("&lt;b&gt;", charts.bar_chart([("<b>", 1.0)]))


class FormatTests(unittest.TestCase):
    """Formatting helpers must render missing data as an em dash, never crash."""

    def test_missing_values(self) -> None:
        for func in (fmt.num, fmt.usd, fmt.pct, fmt.sol):
            self.assertEqual(func(None), fmt.DASH)

    def test_usd_abbreviations(self) -> None:
        self.assertEqual(fmt.usd(1_234_000_000), "$1.23B")
        self.assertEqual(fmt.usd(-4_500_000), "-$4.50M")
        self.assertEqual(fmt.usd(12.5), "$12.50")

    def test_signed_percentages(self) -> None:
        self.assertEqual(fmt.pct(3.14159, 2, True), "+3.14%")
        self.assertEqual(fmt.pct(-1.0, 1), "-1.0%")

    def test_relative_time(self) -> None:
        from datetime import datetime, timezone
        now = datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc)
        self.assertEqual(fmt.ago("2026-08-26T11:30:00Z", now), "30 min ago")
        self.assertEqual(fmt.ago("2026-08-25T12:00:00Z", now), "24 hr ago")

    def test_truncate_adds_an_ellipsis(self) -> None:
        self.assertEqual(fmt.truncate("abcdef", 4), "abc…")
        self.assertEqual(fmt.truncate("abc", 10), "abc")


if __name__ == "__main__":
    unittest.main()
