"""Tests use constructed fixtures, never market-data substitutes in published reports."""
import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_performance import evaluate_signal, build

class PerformanceTests(unittest.TestCase):
    def test_weekend_baseline_and_d1(self):
        dates=["2026-10-15","2026-10-16","2026-10-19","2026-10-20"]
        q={
          "2026-10-15":{"601985":10},
          "2026-10-16":{"601985":10.5},
          "2026-10-19":{"601985":9.9},
          "2026-10-20":{"601985":10.1},
        }
        result=evaluate_signal({"date":"2026-10-18","code":"601985","name":"测试","pool":"B","report_status":"summary"},dates,q)
        self.assertEqual(result["reference_date"],"2026-10-16")
        self.assertEqual(result["checkpoints"]["d1"]["date"],"2026-10-19")
        self.assertAlmostEqual(result["checkpoints"]["d1"]["return_pct"],-5.714)
        self.assertIsNone(result["checkpoints"]["d3"])
        self.assertEqual(result["tradability"].split(";")[0],"unverified")

    def test_d3_uses_third_trading_day(self):
        dates=["2026-10-15","2026-10-16","2026-10-19","2026-10-20"]
        q={d:{"003816":v} for d,v in zip(dates,[4,4.1,4.2,4.3])}
        r=evaluate_signal({"date":"2026-10-15","code":"003816","name":"测试","report_status":"summary"},dates,q)
        self.assertEqual(r["checkpoints"]["d3"]["date"],"2026-10-20")
        self.assertEqual(r["checkpoints"]["d3"]["return_pct"],7.5)
        self.assertIsNone(r["checkpoints"]["d5"])

    def test_missing_quotes_do_not_create_fake_profit(self):
        dates=["2026-10-15","2026-10-16"]
        result=evaluate_signal({"date":"2026-10-15","code":"000001","name":"测试"},dates,{"2026-10-15":{},"2026-10-16":{"000001":8}})
        self.assertIsNone(result["reference_close"])
        self.assertIsNone(result["checkpoints"]["d1"]["return_pct"])

    def test_build_from_mock_verified_snapshots(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)
            snapshot=p/"snapshots";snapshot.mkdir()
            candidates=p/"candidates.json"
            candidates.write_text(json.dumps({"records":[{"date":"2026-10-15","code":"600001","name":"测试","role":"watchlist"}]}),encoding="utf-8")
            index=p/"index.json";index.write_text(json.dumps({"dates":["2026-10-15","2026-10-16"]}))
            for day,price in [("2026-10-15",10),("2026-10-16",11)]:
                stocks=[{"code":str(600000+i),"price":price} for i in range(3000)]
                (snapshot/(day+".json")).write_text(json.dumps({
                    "date":day,"stocks":stocks,"quality":{"status":"test_fixture"},
                    "data_sources":[{"provider":"fixture"}]}),encoding="utf-8")
            result=build(candidates,index,snapshot)
            self.assertEqual(result["summary"]["d1_observed"],1)
            self.assertEqual(result["summary"]["d1_positive"],1)
            self.assertEqual(result["records"][0]["checkpoints"]["d1"]["return_pct"],10.0)
            self.assertTrue(result["summary"]["no_actual_trades_logged"])

    def test_reconstructed_report_does_not_inflate_prior_signal_win_rate(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)
            snapshots=p/"snapshots";snapshots.mkdir()
            cand=p/"candidates.json";index=p/"index.json"
            cand.write_text(json.dumps({"records":[
                {"date":"2026-10-22","code":"600001","name":"Actual","role":"watchlist"},
                {"date":"2026-10-22","code":"600002","name":"Reconstructed",
                 "role":"watchlist","report_type":"historical_reconstruction",
                 "reconstructed_at":"2026-10-26"}]}),encoding="utf-8")
            index.write_text(json.dumps({"dates":["2026-10-22","2026-10-23"]}),encoding="utf-8")
            for day,base in [("2026-10-22",10),("2026-10-23",11)]:
                rows=[{"code":str(600000+i),"price":base} for i in range(3000)]
                (snapshots/(day+".json")).write_text(json.dumps({
                    "date":day,"stocks":rows,"data_sources":[],"quality":{"status":"test"}
                }),encoding="utf-8")
            result=build(cand,index,snapshots)
            self.assertEqual(result["summary"]["watchlist_rows"],1)
            self.assertEqual(result["summary"]["reconstructed_rows_excluded"],1)
            self.assertEqual(result["summary"]["d1_positive"],1)
            self.assertEqual({r["code"] for r in result["records"]},{"600001"})
            self.assertEqual({r["code"] for r in result["retrospective_records"]},{"600002"})
            self.assertEqual(result["retrospective_records"][0]["classification"],
                             "later_reconstruction_not_original_scheduled_push")

if __name__=="__main__":
    unittest.main()
