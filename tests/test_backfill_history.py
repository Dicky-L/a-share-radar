"""Tests for historical backfill, with synthetic fixtures NEVER shipped as market data."""
import json
import tempfile
import unittest
from pathlib import Path
from scripts.backfill_history_shard import parse_bar
from scripts.merge_history import merge,save

FIELDS="date,code,open,high,low,close,preclose,volume,amount,adjustflag,turn,tradestatus,pctChg,isST".split(",")

def bar(day="2026-10-19",code="600000",amount="100000000.00",price="10.00",state="1"):
    return [day,"sh."+code,"9.5","10.1","9.4",price,"9.8","10000",
            amount,"3","1.0",state,"2.04","0"]

class HistoryBackfillTest(unittest.TestCase):
    def test_unadjusted_bar_format(self):
        x=parse_bar(bar(),FIELDS,"600000",{"2026-10-19"})
        self.assertEqual(x["price"],10)
        self.assertEqual(x["turnover_yi"],1.0)
        self.assertEqual(x["change_pct"],2.04)

    def test_missing_not_imputed(self):
        self.assertIsNone(parse_bar(bar(day="2026-10-18"),FIELDS,"600000",{"2026-10-19"}))
        self.assertIsNone(parse_bar(bar(state="0"),FIELDS,"600000",{"2026-10-19"}))

    def test_full_merge_and_old_snapshot_preservation(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            universe=[{"code":str(600000+i),"name":"TEST"} for i in range(3000)]
            source=root/"source.json"
            source.write_text(json.dumps({"date":"2026-10-20","stocks":universe}))
            pieces=root/"parts"
            pieces.mkdir()
            for shard in range(2):
                rows=[
                    {"date":"2026-10-19","code":str(600000+i),"name":"TEST",
                     "price":10.0,"change_pct":0.0,"turnover_yi":1.0}
                    for i in range(3000) if i%2==shard
                ]
                (pieces/("part-%02d.json"%shard)).write_text(json.dumps({
                    "shard":shard,"shards":2,"start":"2026-10-19","end":"2026-10-20",
                    "trading_days":["2026-10-19"],"universe_count":3000,
                    "bars":rows,"failed":[]
                }))
            rows=merge(sorted(pieces.glob("*.json")),source_path=source,shards=2)
            self.assertEqual(set(rows),{"2026-10-19"})
            item=rows["2026-10-19"]
            self.assertEqual(set(item),{"schema_version","date","market","sectors","stocks","quality","data_sources"})
            self.assertEqual(item["market"]["turnover_yi"],3000)
            self.assertEqual(item["quality"]["price_basis"],"不复权收盘价")
            out=root/"data"
            (out/"snapshots").mkdir(parents=True)
            (out/"snapshots/2026-10-20.json").write_text(json.dumps({
                "date":"2026-10-20","stocks":universe,"market":{"turnover_yi":200.0}
            }))
            first,old=save(rows,out)
            self.assertEqual(first,["2026-10-19"])
            self.assertEqual(old,[])
            idx=json.loads((out/"index.json").read_text())
            self.assertEqual(idx["dates"],["2026-10-19","2026-10-20"])

    def test_reject_partial_shard_bundle(self):
        with tempfile.TemporaryDirectory() as d:
            src=Path(d)/"source.json"
            src.write_text(json.dumps({"date":"2026-10-20",
                                       "stocks":[{"code":str(600000+i),"name":"X"} for i in range(3000)]}))
            partial=Path(d)/"part-00.json"
            partial.write_text(json.dumps({"shard":0,"shards":2,"universe_count":3000,
                                           "trading_days":["2026-10-19"],"bars":[]}))
            with self.assertRaises(ValueError):
                merge([partial],source_path=src,shards=2)

if __name__=="__main__":
    unittest.main()
