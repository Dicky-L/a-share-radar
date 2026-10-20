"""Offline synthetic FIXTURES for chart ETL validation. NEVER published as market data."""
import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_chart_data import build, summarize


class ChartDataTest(unittest.TestCase):
    def fixture(self, directory: Path, day="2026-10-20", total=3000.0, stale=False):
        rows = []
        for i in range(3000):
            rows.append({
                "code": str(600000 + i),
                "name": "synthetic-fixture-" + str(i),
                "turnover_yi": 1.0,
                "change_pct": 1.0 if i < 1000 else (-1.0 if i < 2000 else 0.0),
            })
        data = {
            "date": "2026-10-19" if stale else day,
            "market": {"turnover_yi": total, "scope": "synthetic test fixture, NOT market data"},
            "stocks": rows,
            "quality": {"status": "partial", "coverage_pct": 100},
            "sectors": [],
            "data_sources": [],
        }
        file = directory / (day + ".json")
        file.write_text(json.dumps(data), encoding="utf-8")
        return file

    def test_breadth_partition_and_top10(self):
        with tempfile.TemporaryDirectory() as temp:
            f = self.fixture(Path(temp))
            row = summarize(f)
            self.assertEqual(row["breadth"], {"up": 1000, "down": 1000, "flat": 1000, "missing": 0})
            self.assertEqual(row["stock_count"], 3000)
            self.assertEqual(row["market_turnover_yi"], 3000.0)
            self.assertEqual(len(row["top_turnover"]), 10)

    def test_reject_mismatching_date(self):
        with tempfile.TemporaryDirectory() as temp:
            f = self.fixture(Path(temp), stale=True)
            with self.assertRaises(ValueError):
                summarize(f)

    def test_reject_inconsistent_market_total(self):
        with tempfile.TemporaryDirectory() as temp:
            f = self.fixture(Path(temp), total=500.0)
            with self.assertRaises(ValueError):
                summarize(f)

    def test_build_empty_does_not_fabricate(self):
        with tempfile.TemporaryDirectory() as temp:
            doc = build(Path(temp))
            self.assertEqual(doc["days"], [])


if __name__ == "__main__":
    unittest.main()
