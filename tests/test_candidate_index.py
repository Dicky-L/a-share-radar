"""Synthetic-only candidate extraction tests; do not publish any fixture stocks."""
import tempfile
import unittest
from pathlib import Path

from scripts.build_candidate_index import build, extract


class CandidateArchiveTest(unittest.TestCase):
    def test_watchlist_with_explicit_triggers(self):
        text = """## 观察候选

| 池别 | 股票 | 代码 | 观察逻辑 | 买入触发 | 失效价 | 卖出计划 |
|---|---|---|---|---|---|---|
| B | 合成案例甲 | 300123 | 缩量企稳 | 放量收盘站稳 | 失效位另核 | 分批止盈 |
"""
        r = extract(text, "2026-10-20", "original")
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]["pool"], "B")
        self.assertEqual(r[0]["entry_trigger"], "放量收盘站稳")
        self.assertEqual(r[0]["invalidation"], "失效位另核")
        self.assertEqual(r[0]["role"], "watchlist")

    def test_review_not_mistaken_as_new_recommendation(self):
        text = """## 历史复盘

| 股票 | 代码 | 复盘结论 |
|---|---|---|
| 合成案例乙 | 600123 | 不满足条件 |
"""
        r = extract(text, "2026-10-20", "summary")
        self.assertEqual(r[0]["role"], "historical_review")
        self.assertIsNone(r[0]["entry_trigger"])
        self.assertIsNone(r[0]["exit_plan"])

    def test_missing_risk_management_not_fabricated(self):
        text = """## 观察池

| 股票 | 代码 |
|---|---|
| 合成案例丙 | 000123 |
"""
        r = extract(text, "2026-10-20", "summary")
        self.assertIsNone(r[0]["pool"])
        self.assertIsNone(r[0]["entry_trigger"])
        self.assertIsNone(r[0]["no_chase"])
        self.assertIsNone(r[0]["invalidation"])
        self.assertIsNone(r[0]["exit_plan"])

    def test_no_match_returns_empty(self):
        self.assertEqual(extract("## 候选\\n没有符合条件股票。","2026-10-20","original"), [])

    def test_reject_wrong_report_date(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root / "2026-10-20.md").write_text(
                "---\\ndate: 2026-10-19\\nstatus: original\\n---\\n# 内容",
                encoding="utf-8"
            )
            with self.assertRaises(ValueError):
                build(root)

    def test_build_summary_and_original_provenance(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root / "2026-10-20.md").write_text(
                "---\ndate: 2026-10-20\nstatus: summary\n---\n## 观察池\n\n"
                "| 池别 | 股票 | 代码 |\n|---|---|---|\n| B | 合成案例丁 | 300123 |\n",
                encoding="utf-8"
            )
            archive=build(root)
            self.assertEqual(len(archive["records"]), 1)
            self.assertEqual(archive["records"][0]["report_status"], "summary")

    def test_recovered_2026_10_19_china_nuclear_has_real_conditions(self):
        archive = build(Path(__file__).resolve().parents[1] / "reports")
        matched = [r for r in archive["records"] if r["date"] == "2026-10-19"
                   and r["code"] == "601985" and r["role"] == "watchlist"]
        self.assertEqual(len(matched), 1)
        item = matched[0]
        self.assertIn("9.58", item["entry_trigger"])
        self.assertIn("9.34", item["invalidation"])
        self.assertIn("10.06", item["exit_plan"])
        self.assertEqual(item["report_status"], "summary")
        self.assertIn("历史", item["supplement_source"])


    def test_pre_oct17_archive_provenance_and_roles(self):
        archive = build(Path(__file__).resolve().parents[1] / "reports")
        entries = archive["records"]
        retrospective = [x for x in entries if x["date"]=="2026-10-13"
                         and x["role"]=="historical_review"]
        actual_14 = [x for x in entries if x["date"]=="2026-10-14"
                     and x["role"]=="watchlist"]
        actual_16 = [x for x in entries if x["date"]=="2026-10-16"
                     and x["role"]=="watchlist"]
        self.assertEqual(len(retrospective), 10)
        self.assertEqual(len(actual_14), 10)
        self.assertEqual({x["pool"] for x in actual_14}, {None})
        self.assertEqual({x["code"] for x in actual_16}, {"601985", "003816", "600886"})
        self.assertTrue(all(x["pool"]=="B" for x in actual_16))
        self.assertTrue(all(x["report_status"]=="summary" for x in retrospective+actual_14+actual_16))



if __name__=="__main__":
    unittest.main()
