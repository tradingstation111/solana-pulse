"""Tests for the parsers: raw blocks, RSS/Atom feeds and SIMD pull requests.

Fixtures are real payloads recorded from mainnet and GitHub, trimmed for size.
No test touches the network.
"""

from __future__ import annotations

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collectors import news  # noqa: E402
from collectors.blocks import _chapman_estimate, summarise_block  # noqa: E402
from core.config import VOTE_PROGRAM_ID  # noqa: E402

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def _fixture(name: str) -> str:
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as handle:
        return handle.read()


class BlockSummaryTests(unittest.TestCase):
    """Fee, failure and wallet statistics derived from a real mainnet block."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.block = json.loads(_fixture("block.json"))
        cls.summary = summarise_block(cls.block)

    def test_transaction_counts_are_consistent(self) -> None:
        s = self.summary
        self.assertEqual(s["tx_count"], len(self.block["transactions"]))
        self.assertEqual(s["tx_count"], s["vote_tx_count"] + s["user_tx_count"])
        self.assertGreater(s["vote_tx_count"], 0)
        self.assertGreater(s["user_tx_count"], 0)

    def test_vote_transactions_are_identified_by_program_id(self) -> None:
        expected = sum(
            1 for tx in self.block["transactions"]
            if any(k["pubkey"] == VOTE_PROGRAM_ID for k in tx["transaction"]["accountKeys"])
        )
        self.assertEqual(self.summary["vote_tx_count"], expected)

    def test_failure_rate_excludes_vote_transactions(self) -> None:
        """Vote transactions almost never fail; including them understates the rate."""
        s = self.summary
        self.assertAlmostEqual(
            s["failure_rate_pct"], s["failed_user_tx_count"] / s["user_tx_count"] * 100)

    def test_fee_percentiles_are_ordered(self) -> None:
        s = self.summary
        self.assertLessEqual(s["median_user_fee_lamports"], s["p90_user_fee_lamports"])
        self.assertGreaterEqual(s["median_user_fee_lamports"], 5000)  # base fee floor

    def test_priority_fee_is_never_negative(self) -> None:
        self.assertGreaterEqual(self.summary["median_priority_fee_lamports"], 0)

    def test_fee_payers_are_collected_from_user_transactions_only(self) -> None:
        s = self.summary
        self.assertGreater(s["unique_fee_payers"], 0)
        self.assertLessEqual(s["unique_fee_payers"], s["user_tx_count"])

    def test_empty_block_does_not_raise(self) -> None:
        summary = summarise_block({"blockTime": 1, "parentSlot": 10, "transactions": []})
        self.assertEqual(summary["tx_count"], 0)
        self.assertIsNone(summary["failure_rate_pct"])
        self.assertIsNone(summary["median_user_fee_lamports"])


class ChapmanEstimatorTests(unittest.TestCase):
    """Capture-recapture population estimate."""

    def test_complete_overlap_estimates_the_observed_set(self) -> None:
        self.assertAlmostEqual(_chapman_estimate(100, 100, 100), 100.0, places=0)

    def test_partial_overlap_estimates_a_larger_population(self) -> None:
        self.assertGreater(_chapman_estimate(100, 100, 25), 300)

    def test_no_overlap_yields_no_estimate(self) -> None:
        self.assertIsNone(_chapman_estimate(100, 100, 0))

    def test_empty_sample_yields_no_estimate(self) -> None:
        self.assertIsNone(_chapman_estimate(0, 5, 0))


class FeedParserTests(unittest.TestCase):
    """One parser has to handle both RSS 2.0 and Atom 1.0."""

    def test_rss_entries(self) -> None:
        items = news.parse_feed(_fixture("feed_rss.xml"), "Solana News")
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["title"], "Alpenglow consensus upgrade explained")
        self.assertEqual(items[0]["link"], "https://solana.com/news/alpenglow")
        self.assertEqual(items[0]["published"], "2026-08-25T14:03:00Z")
        self.assertEqual(items[0]["summary"], "A look at the new consensus protocol.")

    def test_atom_entries_use_the_link_href_attribute(self) -> None:
        items = news.parse_feed(_fixture("feed_atom.xml"), "Agave Releases")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "v3.1.4")
        self.assertTrue(items[0]["link"].endswith("/tag/v3.1.4"))
        self.assertEqual(items[0]["published"], "2026-08-20T11:22:33Z")

    def test_limit_is_respected(self) -> None:
        self.assertEqual(len(news.parse_feed(_fixture("feed_rss.xml"), "x", limit=1)), 1)

    def test_html_is_stripped_and_whitespace_collapsed(self) -> None:
        self.assertEqual(news.clean_text("<p>a   <b>b</b>\n c</p>"), "a b c")

    def test_unparseable_date_returns_none(self) -> None:
        self.assertIsNone(news.parse_date("last Tuesday"))

    def test_missing_date_returns_none(self) -> None:
        self.assertIsNone(news.parse_date(None))


class SimdParserTests(unittest.TestCase):
    """Governance view built from real GitHub pull-request payloads."""

    @classmethod
    def setUpClass(cls) -> None:
        payload = json.loads(_fixture("simd_pulls.json"))
        cls.parsed = news.parse_simd_pulls(payload["open"], payload["closed"])

    def test_open_and_merged_are_separated(self) -> None:
        self.assertEqual(self.parsed["open_count"], len(self.parsed["open"]))
        for pull in self.parsed["open"]:
            self.assertEqual(pull["state"], "open")
        for pull in self.parsed["recently_merged"]:
            self.assertEqual(pull["state"], "merged")
            self.assertIsNotNone(pull["merged_at"])

    def test_open_pulls_are_sorted_newest_first(self) -> None:
        stamps = [p["updated_at"] for p in self.parsed["open"] if p["updated_at"]]
        self.assertEqual(stamps, sorted(stamps, reverse=True))

    def test_simd_number_extraction(self) -> None:
        cases = {
            "SIMD-0326: Alpenglow": 326,
            "simd 525 something": 525,
            "Add SIMD-0001 proposal": 1,
            "No number in this title": None,
        }
        for title, expected in cases.items():
            self.assertEqual(news._simd_number(title), expected, title)

    def test_highlight_matching_is_case_insensitive(self) -> None:
        parsed = news.parse_simd_pulls(
            [{"number": 1, "title": "SIMD-0326: ALPENGLOW consensus", "html_url": "u",
              "user": {"login": "a"}, "labels": []}], [])
        self.assertTrue(parsed["open"][0]["highlight"])
        self.assertEqual(len(parsed["highlighted"]), 1)

    def test_unrelated_title_is_not_highlighted(self) -> None:
        parsed = news.parse_simd_pulls(
            [{"number": 2, "title": "Fix a typo in the readme", "html_url": "u",
              "user": {"login": "a"}, "labels": []}], [])
        self.assertFalse(parsed["open"][0]["highlight"])


if __name__ == "__main__":
    unittest.main()
