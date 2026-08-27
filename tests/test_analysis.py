"""Tests for anomaly detection, history handling and derived statistics.

All tests are offline: they use recorded fixtures and synthetic series, never
the network.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis import anomaly, history  # noqa: E402
from collectors.rpc import _nakamoto  # noqa: E402
from core import config  # noqa: E402


class RobustZTests(unittest.TestCase):
    """The modified z-score is the backbone of statistical detection."""

    def test_value_at_median_scores_zero(self) -> None:
        z, median, _ = anomaly.robust_z(10.0, [8, 9, 10, 11, 12])
        self.assertAlmostEqual(z, 0.0)
        self.assertEqual(median, 10)

    def test_outlier_scores_above_warn_threshold(self) -> None:
        baseline = [100, 101, 99, 100, 102, 98, 100, 101]
        z, _, _ = anomaly.robust_z(140.0, baseline)
        self.assertGreater(abs(z), config.ROBUST_Z_WARN)

    def test_single_earlier_spike_does_not_mask_the_next(self) -> None:
        """This is why MAD is used instead of standard deviation."""
        baseline = [100, 101, 99, 100, 500, 100, 101, 99]
        z, _, _ = anomaly.robust_z(140.0, baseline)
        self.assertGreater(abs(z), config.ROBUST_Z_WARN)

    def test_flat_baseline_with_step_change_still_flags(self) -> None:
        z, _, _ = anomaly.robust_z(50.0, [10] * 8)
        self.assertIsNotNone(z)
        self.assertGreaterEqual(abs(z), config.ROBUST_Z_WARN)

    def test_flat_baseline_with_no_change_is_quiet(self) -> None:
        z, _, _ = anomaly.robust_z(10.0, [10] * 8)
        self.assertEqual(z, 0.0)

    def test_too_little_data_returns_no_score(self) -> None:
        z, _, _ = anomaly.robust_z(10.0, [10])
        self.assertIsNone(z)


class StatisticalDetectorTests(unittest.TestCase):
    """Direction-awareness, relative-change floors and baseline gating."""

    @staticmethod
    def _hist(metric: str, values: list[float]) -> list[dict[str, float]]:
        return [{"ts": f"2026-01-01T00:{i:02d}:00Z", metric: v} for i, v in enumerate(values)]

    def test_quiet_until_minimum_history(self) -> None:
        alerts, scores = anomaly.detect_statistical(
            {"tps": 9000.0}, self._hist("tps", [3000, 3010, 2990]))
        self.assertEqual(alerts, [])
        self.assertEqual(scores["tps"]["status"], "baseline_building")

    def test_tps_spike_is_flagged_once_baseline_exists(self) -> None:
        alerts, _ = anomaly.detect_statistical(
            {"tps": 9000.0}, self._hist("tps", [3000, 3010, 2990, 3005, 2995, 3001, 3002]))
        self.assertEqual([a.metric for a in alerts], ["tps"])
        self.assertIn("spike", alerts[0].title)

    def test_rising_nakamoto_never_alerts(self) -> None:
        """More decentralisation is good news and must not raise an alert."""
        alerts, _ = anomaly.detect_statistical(
            {"nakamoto_coefficient": 40.0},
            self._hist("nakamoto_coefficient", [19, 19, 20, 19, 19, 20, 19]))
        self.assertEqual(alerts, [])

    def test_falling_nakamoto_does_alert(self) -> None:
        alerts, _ = anomaly.detect_statistical(
            {"nakamoto_coefficient": 4.0},
            self._hist("nakamoto_coefficient", [19, 19, 20, 19, 19, 20, 19]))
        self.assertEqual([a.metric for a in alerts], ["nakamoto_coefficient"])

    def test_statistically_odd_but_trivially_small_move_is_suppressed(self) -> None:
        """A metric with a tiny MAD should not alert on a negligible change."""
        baseline = self._hist("validator_count", [1000, 1000, 1000, 1001, 1000, 1000, 1000])
        alerts, _ = anomaly.detect_statistical({"validator_count": 995.0}, baseline)
        self.assertEqual(alerts, [])


class ThresholdRuleTests(unittest.TestCase):
    """Absolute rules must fire regardless of what history says."""

    def _run(self, metrics: dict, sections: dict | None = None) -> list[anomaly.Alert]:
        return anomaly.detect_rules({"metrics": metrics, "sections": sections or {}})

    def test_unhealthy_cluster_is_critical(self) -> None:
        alerts = self._run({}, {"cluster": {"health": "unhealthy: behind by 900 slots"}})
        self.assertEqual(alerts[0].severity, "critical")
        self.assertEqual(alerts[0].metric, "cluster_health")

    def test_healthy_cluster_is_silent(self) -> None:
        self.assertEqual(self._run({}, {"cluster": {"health": "ok"}}), [])

    def test_slot_time_bands(self) -> None:
        self.assertEqual(self._run({"slot_time_ms": 400})[:1], [])
        self.assertEqual(self._run({"slot_time_ms": 700})[0].severity, "warning")
        self.assertEqual(self._run({"slot_time_ms": 900})[0].severity, "critical")

    def test_delinquent_stake_bands(self) -> None:
        self.assertEqual(self._run({"delinquent_stake_pct": 0.5}), [])
        self.assertEqual(self._run({"delinquent_stake_pct": 3.0})[0].severity, "warning")
        self.assertEqual(self._run({"delinquent_stake_pct": 9.0})[0].severity, "critical")

    def test_normal_bot_failure_rate_does_not_alert(self) -> None:
        """Solana's user failure rate normally sits between 30% and 50%."""
        self.assertEqual(self._run({"tx_failure_rate_pct": 45.0}), [])
        self.assertEqual(self._run({"tx_failure_rate_pct": 80.0})[0].metric, "tx_failure_rate_pct")

    def test_client_monoculture_is_flagged(self) -> None:
        self.assertEqual(self._run({"dominant_client_pct": 92.0})[0].metric, "dominant_client_pct")
        self.assertEqual(self._run({"dominant_client_pct": 60.0}), [])

    def test_degraded_status_component_is_surfaced(self) -> None:
        alerts = self._run({}, {"status": {"degraded_components": [
            {"name": "Mainnet Beta - Cluster", "status": "partial_outage"}]}})
        self.assertEqual(alerts[0].metric, "status_page")


class CorrelationDetectorTests(unittest.TestCase):
    """Cross-source checks a single-source dashboard could not make."""

    def test_price_and_tvl_divergence(self) -> None:
        alerts = anomaly.detect_correlations(
            {"metrics": {"change_24h_pct": -12.0}, "sections": {"tvl": {"change_1d_pct": 1.5}}}, [])
        self.assertEqual([a.metric for a in alerts], ["tvl_price_divergence"])

    def test_aligned_price_and_tvl_are_quiet(self) -> None:
        alerts = anomaly.detect_correlations(
            {"metrics": {"change_24h_pct": -8.0}, "sections": {"tvl": {"change_1d_pct": -7.0}}}, [])
        self.assertEqual(alerts, [])

    def test_fee_to_volume_ratio_shift(self) -> None:
        past = [{"ts": str(i), "dex_volume_24h_usd": 2e9, "chain_fees_24h_usd": 1e7} for i in range(8)]
        alerts = anomaly.detect_correlations(
            {"metrics": {"dex_volume_24h_usd": 2e9, "chain_fees_24h_usd": 6e7}, "sections": {}}, past)
        self.assertIn("fee_to_volume_ratio", [a.metric for a in alerts])


class HistoryTests(unittest.TestCase):
    """The append-only store must survive partial writes and stay bounded."""

    def test_round_trip_and_trim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "h.jsonl")
            for i in range(6):
                history.append_record({"ts": f"2026-01-01T00:0{i}:00Z", "tps": 1000 + i},
                                      path=path, max_records=4)
            records = history.load_history(path)
            self.assertEqual(len(records), 4)
            self.assertEqual(records[-1]["tps"], 1005)

    def test_malformed_line_is_skipped_not_fatal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "h.jsonl")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write('{"ts":"2026-01-01T00:00:00Z","tps":1}\n')
                handle.write('{"ts":"truncated mid-wri\n')
                handle.write('{"ts":"2026-01-01T00:01:00Z","tps":2}\n')
            records = history.load_history(path)
            self.assertEqual([r["tps"] for r in records], [1, 2])

    def test_build_record_keeps_only_tracked_numeric_metrics(self) -> None:
        record = history.build_record("2026-01-01T00:00:00Z", {
            "tps": 4000.5, "price_usd": 100.0, "validators": ["not", "numeric"],
            "some_unlisted_metric": 7,
        })
        self.assertEqual(set(record), {"ts", "tps", "price_usd"})

    def test_series_extracts_numeric_pairs_in_order(self) -> None:
        records = [{"ts": "a", "tps": 1}, {"ts": "b"}, {"ts": "c", "tps": 3}]
        self.assertEqual(history.series(records, "tps"), [("a", 1.0), ("c", 3.0)])


class NakamotoTests(unittest.TestCase):
    """The superminority count must match a hand-worked example."""

    def test_two_validators_hold_the_superminority(self) -> None:
        stakes = [30, 20, 10, 10, 10, 10, 10]  # total 100; 30+20 = 50% > 33.3%
        self.assertEqual(_nakamoto(stakes, 100.0), 2)

    def test_perfectly_even_stake_needs_a_third_of_the_set(self) -> None:
        stakes = [10] * 9
        self.assertEqual(_nakamoto(stakes, 90.0), 4)  # 4 x 10 = 44% > 33.3%

    def test_single_dominant_validator(self) -> None:
        self.assertEqual(_nakamoto([90, 5, 5], 100.0), 1)


if __name__ == "__main__":
    unittest.main()
