"""AKShare post-close snapshot; refuse unverifiable dates and partial stock universes."""
import json, os, pathlib
from datetime import datetime
from zoneinfo import ZoneInfo
import akshare as ak

ROOT=pathlib.Path(__file__).resolve().parent
OUT=ROOT/"data"
NOW=datetime.now(ZoneInfo("Asia/Shanghai"))
DAY=NOW.strftime("%Y-%m-%d")

def num(x):
    try:
        v=float(str(x).replace(",",""))
        return round(v,4) if v==v and abs(v)!=float("inf") else None
    except (TypeError,ValueError): return None

def main():
    if NOW.hour<15 or (NOW.hour==15 and NOW.minute<20):
        print("Before Shanghai 15:20 close snapshot window; skip")
        return
    cal=ak.tool_trade_date_hist_sina()
    days=set(str(x)[:10] for x in cal["trade_date"])
    if DAY not in days:
        print("Closed market",DAY)
        return
    dated=ak.stock_market_fund_flow()
    if "日期" not in dated.columns or dated.empty:
        raise RuntimeError("Cannot verify upstream market date")
    newest=max(str(x)[:10] for x in dated["日期"].dropna())
    if newest != DAY:
        raise RuntimeError("Upstream flow date is "+newest+", not "+DAY)
    data=ak.stock_zh_a_spot_em()
    mandatory={"代码","名称","最新价","成交额"}
    if not mandatory.issubset(set(data.columns)):
        raise RuntimeError("Upstream stock quote schema mismatch")
    stocks=[]
    market=0
    for _,r in data.iterrows():
        code=str(r["代码"]).zfill(6)
        if not code.startswith(("60","68","00","30")): continue
        price,turn=num(r["最新价"]),num(r["成交额"])
        if price is None or price<=0 or turn is None or turn<0:continue
        market+=turn
        name=str(r["名称"])
        if code.startswith("68") or "ST" in name.upper() or "退" in name:continue
        stocks.append({"code":code,"name":name,"price":price,"change_pct":num(r.get("涨跌幅")),"turnover_yi":round(turn/1e8,4)})
    if len(stocks)<3000: raise RuntimeError("Incomplete stock universe: "+str(len(stocks)))
    payload={
      "schema_version":1,"date":DAY,
      "market":{"turnover_yi":round(market/1e8,4),"scope":"沪深A股股票（含科创板，非ETF，非北交所）"},
      "sectors":[],
      "stocks":stocks,
      "quality":{"status":"partial","message":"真实沪深A股股票行情已核验；行业双日资金需要完整成分与同源资金数据，暂不发布假数值。"},
      "data_sources":[{"provider":"AKShare / Eastmoney","api":"stock_zh_a_spot_em","verified_by":"stock_market_fund_flow 日期核验"}]
    }
    (OUT/"snapshots").mkdir(parents=True,exist_ok=True)
    path=OUT/"snapshots"/(DAY+".json")
    path.write_text(json.dumps(payload,ensure_ascii=False,allow_nan=False,separators=(",",":"))+"\n",encoding="utf-8")
    dates=sorted(p.stem for p in (OUT/"snapshots").glob("????-??-??.json"))
    (OUT/"index.json").write_text(json.dumps({"schema_version":1,"latest_date":dates[-1],"dates":dates,"source":"AKShare real post-close, partial sectors"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (OUT/"latest.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("VERIFIED",DAY,len(stocks),"stocks, market turnover",payload["market"]["turnover_yi"],"亿元")

if __name__=="__main__":main()
