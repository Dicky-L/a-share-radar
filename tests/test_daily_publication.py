import tempfile
import unittest
from pathlib import Path
from scripts.check_daily_publication import verify

class DailyPublishTest(unittest.TestCase):
    def test_missing_is_a_failure(self):
        with tempfile.TemporaryDirectory() as d:
            ok,_=verify("2026-10-22",Path(d))
            self.assertFalse(ok)

    def test_only_summary_is_not_full_report(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d,"2026-10-22.md").write_text(
                "---\ndate: 2026-10-22\nstatus: summary\n---\n# 摘要\n",
                encoding="utf-8")
            ok,_=verify("2026-10-22",Path(d))
            self.assertFalse(ok)

    def test_sourced_full_report(self):
        with tempfile.TemporaryDirectory() as d:
            text="---\ndate: 2026-10-22\nstatus: original\nsource: Published task\n---\n"
            text+="# 每日选股日报\n## 市场资金\n"+("真实股票交易观察；"*90)+"\n## 候选股票与卖出条件\n## 历史复盘\n"
            Path(d,"2026-10-22.md").write_text(text,encoding="utf-8")
            ok,_=verify("2026-10-22",Path(d))
            self.assertTrue(ok)

if __name__ == "__main__":
    unittest.main()
