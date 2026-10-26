"""Deterministic synthetic checks. NO fixture values are published as quotes."""
import copy
import json
import hashlib
import tempfile
import unittest
from pathlib import Path

from scripts.replay_asof import (
    POLICY_ID, build, checked_frozen, freeze_selections, load_snapshot, screen,
)


def maker(day, prices, extra_growth=None):
    stocks = {}
    for n in range(3000):
        code = str(600000 + n)
        values = prices.get(code, (10.0, 0.7, 0.0))
        stocks[code] = {
            "code": code, "name": "Test", "close": values[0],
            "turnover": values[1], "day_change": values[2],
        }
    return {"date": day, "stocks": stocks,
            "market": {"turnover_yi": 5000, "scope": "test fixture"}}


class StrictPointInTimeTest(unittest.TestCase):
    def setUp(self):
        self.days = ["2026-10-13","2026-10-14","2026-10-15",
                     "2026-10-16","2026-10-19","2026-10-20","2026-10-21"]
        historical = [10.0,10.1,10.2,10.3,10.35,10.6,11.0]
        self.maps={}
        for i,day in enumerate(self.days):
            px=historical[i]
            self.maps[day]=maker(day,{"600001":(px,2.0 if i==5 else 1.0,3.0 if i==5 else 1.0)})
            # Valid market breadth above gating threshold from a synthetic market.
            for code in list(self.maps[day]["stocks"])[:2000]:
                self.maps[day]["stocks"][code]["day_change"]=1.0
        def fixture(day,asof):
            if day>asof:
                raise AssertionError("FUTURE ACCESS BY SELECTOR")
            return copy.deepcopy(self.maps[day])
        self.fixture=fixture

    def test_frozen_baseline_hash_does_not_permit_silent_rewrites(self):
        selected=freeze_selections(self.days,end="2026-10-20",loader=self.fixture)
        content=json.dumps(selected,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
        frozen={
            "schema_version":1,"policy_id":POLICY_ID,"selection_end":"2026-10-20",
            "selection_hash_sha256":hashlib.sha256(content).hexdigest(),
            "selection":selected,
        }
        checked=checked_frozen(frozen,self.days,stop="2026-10-20")
        self.assertEqual(checked,selected)
        frozen["selection"][5]["signals"][0]["reference_close"]=9999
        with self.assertRaisesRegex(ValueError,"Frozen selection content changed"):
            checked_frozen(frozen,self.days,stop="2026-10-20")

    def test_future_access_is_blocked_by_reader(self):
        with self.assertRaisesRegex(ValueError,"LOOKAHEAD BLOCKED"):
            load_snapshot("2026-10-21","2026-10-20",Path("/does/not/exist"))

    def test_cold_start_does_not_fabricate_signals(self):
        result=screen(self.days[0],self.days,self.fixture)
        self.assertEqual(result["selection_status"],"warmup_insufficient_history")
        self.assertEqual(result["signals"],[])

    def test_asof_unchanged_after_mutating_future_winner(self):
        day="2026-10-20"
        a=screen(day,self.days,self.fixture)
        self.assertEqual(a["policy_id"],POLICY_ID)
        self.assertEqual(a["data_access_ceiling"],day)
        self.assertEqual(a["pool_A"],[])
        self.assertIn("600001",{x["code"] for x in a["signals"]})
        self.assertFalse(a["evidence"]["L3_sector_flow_and_vintaged_catalysts"])
        self.assertFalse(a["evidence"]["L4_vintaged_financial_risk_review"])
        self.maps["2026-10-21"]["stocks"]["600001"]["close"]=9999
        b=screen(day,self.days,self.fixture)
        self.assertEqual(a,b)

    def test_replay_selection_hash_does_not_depend_on_outcomes(self):
        a=build(self.days,self.fixture,stop="2026-10-20")
        self.maps["2026-10-21"]["stocks"]["600001"]["close"]=0.5
        b=build(self.days,self.fixture,stop="2026-10-20")
        self.assertEqual(a["selection_hash_sha256"],b["selection_hash_sha256"])
        self.assertEqual(a["selection"],b["selection"])
        self.assertNotEqual(a["results"],b["results"])
        self.assertIsNone(a["summary"]["actual_original_strategy_accuracy"])
        self.assertIsNone(a["summary"]["actual_executable_profit"])

    def test_future_equal_weight_benchmark_only_in_evaluation(self):
        result=build(self.days,self.fixture,stop="2026-10-20")
        self.assertEqual(result["summary"]["d1_excess_observed"],
                         result["summary"]["d1_observed"])
        self.assertIsNotNone(result["summary"]["d1_mean_excess_vs_equal_weight_pct"])
        for item in result["results"]:
            d1=item["checkpoints"]["d1"]
            if d1 and d1["return_pct"] is not None:
                self.assertAlmostEqual(
                    d1["excess_over_equal_weight_pct"],
                    round(d1["return_pct"]-d1["market_equal_weight_pct"],3))
        self.assertTrue(all("excess_over_equal_weight_pct" not in signal
                            for day in result["selection"] for signal in day["signals"]))

    def test_no_a_pool_even_if_price_score_extreme(self):
        result=screen("2026-10-20",self.days,self.fixture)
        self.assertEqual(result["pool_A"],[])
        self.assertTrue(all(x["classification"]=="TECHNICAL_PRESCREEN_ONLY" for x in result["signals"]))

    def test_weak_breadth_means_no_new_technical_prescreen(self):
        day="2026-10-20"
        for stock in self.maps[day]["stocks"].values():
            stock["day_change"]=-2.0
        result=screen(day,self.days,self.fixture)
        self.assertEqual(result["selection_status"],"market_breadth_too_weak_no_new_entry")
        self.assertEqual(result["signals"],[])


if __name__=="__main__":
    unittest.main()
