"""Fetch a fixed one-month window of real, unadjusted BaoStock daily OHLC data.

Each GitHub Actions shard independently reads the existing, dated Oct 20 universe.
No synthetic values, no fake reports, no direct commit from parallel workers.
"""
import argparse
import json
import logging
import re
import time
from datetime import date
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"data/snapshots/2026-10-20.json"
FIELDS="date,code,open,high,low,close,preclose,volume,amount,adjustflag,turn,tradestatus,pctChg,isST"

def safe_num(v):
    try:
        n=float(v)
        if n!=n or abs(n)==float("inf"):return None
        return n
    except (ValueError,TypeError):return None

def parse_bar(row,fields,expected_code,allow_dates):
    d=dict(zip(fields,row))
    day=d.get("date")
    if day not in allow_dates or d.get("code","").split(".")[-1]!=expected_code:return None
    if d.get("tradestatus")!="1" or d.get("adjustflag")!="3":return None
    price,amount=safe_num(d.get("close")),safe_num(d.get("amount"))
    if price is None or price<=0 or amount is None or amount<0:return None
    pct=safe_num(d.get("pctChg"))
    return {"date":day,"code":expected_code,"price":round(price,4),
            "change_pct":round(pct,4) if pct is not None else None,
            "turnover_yi":round(amount/1e8,6)}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--start",default="2026-09-21")
    p.add_argument("--end",default="2026-10-20")
    p.add_argument("--shard",type=int,required=True)
    p.add_argument("--shards",type=int,default=8)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    if a.shards<1 or a.shards>32 or a.shard<0 or a.shard>=a.shards:
        raise ValueError("Invalid shard range")
    start,end=date.fromisoformat(a.start),date.fromisoformat(a.end)
    if start>end or (end-start).days>45:
        raise ValueError("Historical backfill window must be <=45 days")
    source=json.loads(SOURCE.read_text(encoding="utf-8"))
    if source.get("date")!="2026-10-20" or len(source.get("stocks",[]))<3000:
        raise ValueError("Authoritative Oct 20 stock universe missing")
    names={}
    for x in source["stocks"]:
        code=str(x["code"])
        if re.fullmatch(r"(?:60|68|00|30)\d{4}",code):
            names[code]=str(x["name"])
    codes=sorted(names)
    mine=[code for i,code in enumerate(codes) if i%a.shards==a.shard]
    logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s %(message)s")
    import baostock as bs
    login=bs.login()
    if login.error_code!="0":raise RuntimeError("BaoStock login failed "+login.error_msg)
    try:
        cal=bs.query_trade_dates(start_date=a.start,end_date=a.end)
        if cal.error_code!="0":raise RuntimeError("Calendar unavailable "+cal.error_msg)
        trading=[]
        while cal.next():
            row=dict(zip(cal.fields,cal.get_row_data()))
            if row.get("is_trading_day")=="1":
                trading.append(row["calendar_date"])
        if len(trading)<8 or len(trading)>30:
            raise RuntimeError("Suspicious trade calendar: "+str(trading))
        days=set(trading)
        found=[]
        failed=[]
        for count,code in enumerate(mine,1):
            symbol=("sh." if code.startswith("6") else "sz.")+code
            ok=False
            for attempt in range(2):
                try:
                    result=bs.query_history_k_data_plus(
                        symbol,FIELDS,start_date=a.start,end_date=a.end,
                        frequency="d",adjustflag="3"
                    )
                    if result.error_code!="0":
                        raise RuntimeError(result.error_code+" "+result.error_msg)
                    while result.next():
                        bar=parse_bar(result.get_row_data(),result.fields,code,days)
                        if bar:
                            bar["name"]=names[code] # Names come from dated Oct 20 universe.
                            found.append(bar)
                    ok=True
                    break
                except (Exception) as exc:
                    logging.warning("%s attempt %d: %s",code,attempt+1,exc)
                    if attempt==0:time.sleep(1.0)
            if not ok:failed.append(code)
            if count%100==0:
                logging.info("Shard %d/%d: queried %d/%d tickers, %d valid bars, %d errors",
                             a.shard,a.shards,count,len(mine),len(found),len(failed))
            time.sleep(0.10)
        if len(found)<len(mine)*3 or len(failed)>len(mine)*0.15:
            raise RuntimeError("Shard unusable: "+str(len(found))+" bars and "+str(len(failed))+" errors")
        output=Path(a.output);output.parent.mkdir(parents=True,exist_ok=True)
        payload={"shard":a.shard,"shards":a.shards,"start":a.start,"end":a.end,
                 "trading_days":trading,"universe_count":len(codes),"shard_universe_count":len(mine),
                 "bars":found,"failed":failed,"source":"BaoStock unadjusted daily K data (adjustflag=3)"}
        output.write_text(json.dumps(payload,ensure_ascii=False,allow_nan=False,separators=(",",":"))+"\n",encoding="utf-8")
        logging.info("SHARD OK %s, %d stocks, %d actual bars, %d errors",output,len(mine),len(found),len(failed))
    finally:
        bs.logout()

if __name__=="__main__":main()
