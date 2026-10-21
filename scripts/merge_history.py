"""Merge real historical shard artifacts into Oct-20-compatible daily snapshots.

All shards and every trade day must pass integrity checks. Never overwrite an existing
trusted snapshot, and never fill missing stock bars with zeroes or synthetic prices.
"""
from __future__ import annotations
import argparse
import json
import math
import os
import re
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
DAY_RE=re.compile(r"\d{4}-\d{2}-\d{2}")

def numeric(v):
    return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)

def merge(paths,source_path=DATA/"snapshots/2026-10-20.json",shards=8):
    authoritative=json.loads(source_path.read_text(encoding="utf-8"))
    if authoritative.get("date")!="2026-10-20" or len(authoritative.get("stocks",[]))<3000:
        raise ValueError("Missing verified dated universe")
    universe={str(x["code"]):str(x["name"]) for x in authoritative["stocks"]}
    records=defaultdict(dict)
    calendars=[]
    pieces=[]
    seen=set()
    for p in paths:
        raw=json.loads(Path(p).read_text(encoding="utf-8"))
        shard=raw.get("shard")
        if shard in seen or not isinstance(shard,int) or shard<0 or shard>=shards or raw.get("shards")!=shards:
            raise ValueError("Duplicate/misnumbered shard "+str(shard))
        seen.add(shard);pieces.append(raw)
        days=raw.get("trading_days")
        if not isinstance(days,list) or not days or not all(isinstance(d,str) and DAY_RE.fullmatch(d) for d in days):
            raise ValueError("Invalid trade calendar")
        calendars.append(days)
        if raw.get("universe_count")!=len(universe):
            raise ValueError("Universe changed during backfill")
        for row in raw.get("bars",[]):
            day,code=row.get("date"),str(row.get("code",""))
            if day not in days or code not in universe:
                raise ValueError("Unknown day/ticker")
            if sorted(universe).index(code)%shards!=shard:
                raise ValueError("Ticker in wrong shard")
            if code in records[day]:
                raise ValueError("Duplicated bar "+day+" "+code)
            if not numeric(row.get("price")) or row["price"]<=0 or not numeric(row.get("turnover_yi")) or row["turnover_yi"]<0:
                raise ValueError("Bad price / amount "+code)
            if row.get("change_pct") is not None and not numeric(row["change_pct"]):
                raise ValueError("Bad change percentage")
            records[day][code]=row
    if seen!=set(range(shards)):
        raise ValueError("Missing shard artifacts: "+str(set(range(shards))-seen))
    if any(days!=calendars[0] for days in calendars):
        raise ValueError("Shard trading calendars disagree")
    result={}
    for day in calendars[0]:
        bars=sorted(records[day].values(),key=lambda x:x["code"])
        count=len(bars)
        coverage=count/len(universe)*100
        if count<3000 or coverage<85:
            raise ValueError("Insufficient real market coverage for "+day+": "+str(count)+"/"+str(len(universe)))
        stocks=[{
            "code":x["code"],"name":universe[x["code"]],
            "price":x["price"],"change_pct":x["change_pct"],
            "turnover_yi":round(x["turnover_yi"],4),
        } for x in bars]
        turnover=round(sum(x["turnover_yi"] for x in stocks),4)
        if turnover<=0:raise ValueError("No market turnover "+day)
        result[day]={
            "schema_version":1,"date":day,
            "market":{
                "turnover_yi":turnover,
                "scope":"沪深A股有效个股成交额小计；按2026-10-20上市样本回填，非当日全部上市证券"
            },
            "sectors":[],"stocks":stocks,
            "quality":{
                "status":"historical_partial",
                "coverage_pct":round(coverage,2),
                "universe_asof":"2026-10-20",
                "price_basis":"不复权收盘价",
                "name_basis":"股票名称沿用2026-10-20快照，不保证历史曾用名",
                "message":"BaoStock未复权历史日K；按10月20日股票名录回溯，可能遗漏随后退市/改名股票、停牌及无有效行情股票；成交额是覆盖样本小计。行业资金没有回填。"
            },
            "data_sources":[{"provider":"BaoStock","api":"query_history_k_data_plus",
                             "adjustflag":"3","currency":"CNY","amount_unit":"元",
                             "role":"逐股未复权历史收盘价、涨跌幅、成交额"}]
        }
    return result

def save(result,folder=DATA):
    snapshots=folder/"snapshots";snapshots.mkdir(parents=True,exist_ok=True)
    already=[]
    newly=[]
    for day,payload in sorted(result.items()):
        path=snapshots/(day+".json")
        if path.exists():
            old=json.loads(path.read_text(encoding="utf-8"))
            if old.get("date")!=day or len(old.get("stocks",[]))<3000:
                raise ValueError("Existing dated snapshot is inconsistent: "+day)
            already.append(day);continue
        tmp=path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload,ensure_ascii=False,allow_nan=False,separators=(",",":"))+"\n",encoding="utf-8")
        os.replace(tmp,path)
        newly.append(day)
    dates=sorted(p.stem for p in snapshots.glob("????-??-??.json"))
    if dates:
        existing_index=json.loads((folder/"index.json").read_text(encoding="utf-8")) if (folder/"index.json").exists() else {}
        existing_index.update({"schema_version":1,"latest_date":dates[-1],"dates":dates,
                               "source":"多源盘后快照 + BaoStock未复权历史回填（按日期查看每份质量与来源）"})
        (folder/"index.json").write_text(json.dumps(existing_index,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return newly,already

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--parts",required=True)
    p.add_argument("--shards",type=int,default=8)
    p.add_argument("--dry-run",action="store_true")
    a=p.parse_args()
    paths=sorted(Path(a.parts).rglob("part-*.json"))
    result=merge(paths,shards=a.shards)
    print("Validated %d market days: %s" % (len(result),", ".join(sorted(result))))
    if not a.dry_run:
        new,old=save(result)
        print("Saved %d new days, preserved %d existing trusted snapshots" % (len(new),len(old)))

if __name__=="__main__":main()
