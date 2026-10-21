"""Selection accountability: evaluate dated watchlist CLOSE-TO-CLOSE movements.

This is explicitly NOT executable P&L, strategy win rate, or advice to buy.
No buy-trigger execution, transaction costs, intraday high/low or index benchmark
is inferred from daily close-only snapshots.
"""
from __future__ import annotations
import json
import math
import re
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CANDIDATES=ROOT/"reports"/"candidates.json"
INDEX=ROOT/"data"/"index.json"
SNAPSHOTS=ROOT/"data"/"snapshots"
OUTPUT=ROOT/"reports"/"performance.json"
DATE_RE=re.compile(r"^\d{4}-\d{2}-\d{2}$")

def price(v):
    return float(v) if isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) and v>0 else None

def pct(base,next_close):
    return round((next_close/base-1)*100,3) if base and next_close else None

def evaluate_signal(signal,dates,quotes):
    report_day=signal["date"];ticker=signal["code"]
    # A report after the close has no same-day executable entry. Reference
    # price is only the last known close at or before its publication date.
    history=[d for d in dates if d<=report_day]
    baseline_day=history[-1] if history else None
    baseline=quotes.get(baseline_day,{}).get(ticker) if baseline_day else None
    future=[d for d in dates if d>report_day]
    observed=[]
    for i,day in enumerate(future):
        close=quotes.get(day,{}).get(ticker)
        observed.append({"trading_day":i+1,"date":day,"close":close,"return_pct":pct(baseline,close)})
    checkpoints={}
    for days in (1,3,5,10):
        row=observed[days-1] if len(observed)>=days else None
        checkpoints["d"+str(days)]=dict(row) if row else None
    valid=[x["return_pct"] for x in observed if x["return_pct"] is not None]
    return {
        "date":report_day,"code":ticker,"name":signal["name"],"pool":signal.get("pool"),
        "report_status":signal.get("report_status"),
        "reference_date":baseline_day,"reference_close":baseline,
        "reference_type":"报告日或之前最近有效交易日收盘价，不是实际成交入场价",
        "checkpoints":checkpoints,
        "observations":observed,
        "best_observed_close_change_pct":max(valid) if valid else None,
        "worst_observed_close_change_pct":min(valid) if valid else None,
        "entry_trigger":signal.get("entry_trigger"),
        "invalidation":signal.get("invalidation"),
        "exit_plan":signal.get("exit_plan"),
        "supplement_source":signal.get("supplement_source"),
        "tradability":"unverified; no order, stop, slippage or T+1 execution simulated",
        "source_report":"./reports/"+report_day+".md",
    }

def build(candidates_path=CANDIDATES,index_path=INDEX,snapshots_dir=SNAPSHOTS):
    candidates=json.loads(Path(candidates_path).read_text(encoding="utf-8"))
    index=json.loads(Path(index_path).read_text(encoding="utf-8"))
    dates=sorted(set(index.get("dates",[])))
    if not dates or any(not DATE_RE.fullmatch(d) for d in dates):
        raise ValueError("No verified market date index")
    quotes={}
    coverage={}
    for day in dates:
        p=Path(snapshots_dir)/(day+".json")
        if not p.exists():raise ValueError("Date index points to missing snapshot: "+day)
        doc=json.loads(p.read_text(encoding="utf-8"))
        if doc.get("date")!=day or not isinstance(doc.get("stocks"),list) or len(doc["stocks"])<3000:
            raise ValueError("Invalid snapshot: "+day)
        dayquotes={}
        for row in doc["stocks"]:
            code=str(row.get("code",""))
            p=price(row.get("price"))
            if not re.fullmatch(r"\d{6}",code) or p is None:continue
            if code in dayquotes:raise ValueError("Duplicate stock "+day+" "+code)
            dayquotes[code]=p
        quotes[day]=dayquotes
        coverage[day]={"stocks":len(dayquotes),"source":[x.get("provider") for x in doc.get("data_sources",[])],
                       "quality_status":doc.get("quality",{}).get("status")}
    signals=[x for x in candidates.get("records",[]) if x.get("role")=="watchlist"]
    results=[evaluate_signal(x,dates,quotes) for x in signals]
    d1=[r["checkpoints"]["d1"]["return_pct"] for r in results if r["checkpoints"]["d1"] and r["checkpoints"]["d1"]["return_pct"] is not None]
    d3=[r["checkpoints"]["d3"]["return_pct"] for r in results if r["checkpoints"]["d3"] and r["checkpoints"]["d3"]["return_pct"] is not None]
    return {
        "schema_version":1,
        "method":"REPORT_DATE_LAST_CLOSE_TO_LATER_TRADING_DAY_CLOSE",
        "disclaimer":"真实盘后收盘涨跌观察，不是可执行交易收益、真实账户盈亏或策略胜率。没有验证实际买点是否触发、价格可成交性、滑点、交易费用、T+1、停牌和股息复权。重复出现股票可能使样本相关。",
        "market_dates":dates,"coverage_by_date":coverage,
        "summary":{
            "watchlist_rows":len(results),
            "unique_tickers":len({x["code"] for x in results}),
            "dated_issues":len({x["date"] for x in results}),
            "d1_observed":len(d1),"d1_positive":sum(x>0 for x in d1),
            "d1_zero_or_negative":sum(x<=0 for x in d1),
            "d1_avg_pct":round(sum(d1)/len(d1),3) if d1 else None,
            "d3_observed":len(d3),"d3_positive":sum(x>0 for x in d3),
            "d3_avg_pct":round(sum(d3)/len(d3),3) if d3 else None,
            "no_actual_trades_logged":True,
        },
        "records":results,
    }

def main():
    result=build()
    OUTPUT.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print("Selection tracking built: %d candidate records, D+1 %d, D+3 %d, %d market dates" %
          (result["summary"]["watchlist_rows"],result["summary"]["d1_observed"],
           result["summary"]["d3_observed"],len(result["market_dates"])))

if __name__=="__main__":
    main()
