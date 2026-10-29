"""Prevent a repeated 2026-10-27 electronic-sector discrepancy."""
import tempfile
import json
from datetime import datetime
import unittest
from pathlib import Path
from scripts.check_sector_consistency import verify,table_in_report,canonical

class IndustryPrimaryFlowContract(unittest.TestCase):
    def test_canonical_27_28_electronics(self):
        c=canonical()
        self.assertEqual(str(c["2026-10-27"]["电子"]),"-122.32")
        self.assertEqual(str(c["2026-10-28"]["电子"]),"143.98")
        self.assertEqual(len(c["2026-10-27"]),31)
        self.assertEqual(len(c["2026-10-28"]),31)

    def test_all_primary_fund_tables_match_canonical_source(self):
        observations=verify()
        self.assertEqual(len(observations[("2026-10-27","电子")]),2)
        self.assertEqual(len(set(v for _,v in observations[("2026-10-27","电子")])),1)

    def test_28_must_use_same_prior_day_as_27_report(self):
        report=(Path(__file__).resolve().parents[1]/"reports"/"2026-10-28.md").read_text(encoding="utf-8")
        days,rows,_=table_in_report(report)
        self.assertEqual(days,["2026-10-27","2026-10-28"])
        electronic=next(r for r in rows if r[0]=="电子")
        self.assertEqual(tuple(str(x) for x in electronic[1:]),("-122.32","143.98","266.30"))

    def test_postclose_window_and_source_identity_are_identical(self):
        root=Path(__file__).resolve().parents[1]
        days=("2026-10-27","2026-10-28")
        docs=[json.loads((root/"data"/"industry-flows"/(day+".json")).read_text(encoding="utf-8")) for day in days]
        self.assertEqual(len({x["source_id"] for x in docs}),1)
        self.assertEqual(len({x["industry_classification"] for x in docs}),1)
        self.assertEqual(len({x["metric"] for x in docs}),1)
        self.assertEqual(len({x["unit"] for x in docs}),1)
        self.assertEqual(len(docs[0]["industries"]),31)
        self.assertEqual(len(docs[1]["industries"]),31)
        for day,doc in zip(days,docs):
            self.assertEqual(doc["date"],day)
            published=datetime.fromisoformat(doc["published_at"])
            self.assertEqual(published.date().isoformat(),day)
            self.assertGreaterEqual((published.hour,published.minute),(15,0))
            self.assertLessEqual((published.hour,published.minute),(18,0))
        gap=(datetime.fromisoformat(docs[0]["published_at"])-datetime.fromisoformat(docs[1]["published_at"])).total_seconds()
        self.assertEqual(abs(gap),24*3600-17*60-45)

    def test_oct28_entire_report_uses_canonical_sector_figures(self):
        root=Path(__file__).resolve().parents[1]
        report=(root/"reports/2026-10-28.md").read_text(encoding="utf-8")
        body=report.split("### 跨日报资金口径更正记录",1)[0]
        self.assertNotIn("7.22/+7.46",body)
        self.assertNotIn("23.89亿",body)
        self.assertNotIn("34.23亿",body)
        self.assertIn("银行主力净额+3.54/+6.44亿元",body)
        self.assertIn("27日-0.34亿元、28日+25.97亿元",body)
        self.assertIn("机械行业28日+36.23亿",body)
        self.assertIn("发布时间相差17分45秒",body)

    def test_old_provider_padded_value_is_rejected(self):
        from scripts.check_sector_consistency import REPORTS,STORE
        with tempfile.TemporaryDirectory() as d:
            dest=Path(d)
            for day in ("2026-10-26","2026-10-27","2026-10-28"):
                content=(REPORTS/(day+".md")).read_text(encoding="utf-8")
                if day=="2026-10-28":
                    content=content.replace("| 电子 | -122.32 |","| 电子 | -147.08 |",1)
                (dest/(day+".md")).write_text(content,encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"PRIMARY FLOW MISMATCH"):
                verify(reports=dest,store=STORE)

    def test_mixing_old_other_vendor_current_price_is_rejected(self):
        from scripts.check_sector_consistency import REPORTS,STORE
        with tempfile.TemporaryDirectory() as d:
            dest=Path(d)
            for day in ("2026-10-26","2026-10-27","2026-10-28"):
                content=(REPORTS/(day+".md")).read_text(encoding="utf-8")
                if day=="2026-10-28":
                    content=content.replace("| 电子 | -122.32 | **+143.98** |",
                                            "| 电子 | -122.32 | **+147.23** |",1)
                (dest/(day+".md")).write_text(content,encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"PRIMARY FLOW MISMATCH"):
                verify(reports=dest,store=STORE)

if __name__=="__main__":
    unittest.main()
