"""A股盘后数据：AKShare发现代码，腾讯逐股验证成交日期。失败不发布旧数据。"""
from __future__ import annotations
import json
import logging
import os
import pathlib
import re
import time
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "data"
TZ = ZoneInfo("Asia/Shanghai")
LOG = logging.getLogger("radar")

def normal_code(v):
    m = re.fullmatch(r"(?:sh|sz)?(\d{6})(?:\.(?:sh|sz))?", str(v).strip().lower())
    if not m:
        return None
    code = m.group(1)
    return code if code.startswith(("60", "68", "00", "30")) else None

def num(v):
    try:
        x = float(v)
        return x if x == x and abs(x) != float("inf") else None
    except (ValueError, TypeError):
        return None

def parse_quote(raw, day):
    if '="' not in raw:
        raise ValueError("not a Tencent quote")
    f = raw.split('="', 1)[1].split('"', 1)[0].split("~")
    if len(f) < 38:
        raise ValueError("Tencent quote schema changed")
    code = normal_code(f[2])
    stamp = f[30]
    if not code or not stamp.startswith(day.replace("-", "")) or len(stamp) < 14:
        raise ValueError("stale quote date or invalid ticker")
    if stamp[8:14] < "145500":
        raise ValueError("quote not updated to closing auction")
    price, amount = num(f[3]), num(f[37])
    if price is None or price <= 0 or amount is None or amount < 0:
        raise ValueError("price or turnover unavailable")
    # 腾讯行情字段37单位: 万元；转换成亿元需除以10000。
    return {"code": code, "name": f[1].strip(), "price": round(price, 3),
            "change_pct": num(f[32]), "turnover_yi": round(amount / 10000, 5),
            "quote_time": stamp}

def discover_codes(ak):
    errors = []
    for label, fn in [
        ("AKShare Tencent", ak.stock_zh_a_spot_tx),
        ("AKShare Sina", ak.stock_zh_a_spot),
        ("AKShare Eastmoney", ak.stock_zh_a_spot_em),
    ]:
        try:
            df = fn()
            col = "代码" if "代码" in df.columns else "code"
            codes = sorted({c for v in df[col] if (c := normal_code(v))})
            if len(codes) < 3000:
                raise ValueError("universe incomplete: " + str(len(codes)))
            LOG.info("%s discovered %d securities", label, len(codes))
            return codes, label
        except Exception as exc:
            errors.append(label + ": " + type(exc).__name__ + ": " + str(exc))
            LOG.warning(errors[-1])
    raise RuntimeError("All public stock-universe sources failed: " + " | ".join(errors))

def fetch_quotes(codes, day, request_get=None, batch_size=50):
    import requests
    get = request_get or requests.get
    results = {}
    for n in range(0, len(codes), batch_size):
        batch = codes[n:n + batch_size]
        symbols = ",".join(("sh" if c.startswith("6") else "sz") + c for c in batch)
        for attempt in range(2):
            try:
                response = get("https://qt.gtimg.cn/q=" + symbols,
                               headers={"User-Agent": "Mozilla/5.0",
                                        "Referer": "https://gu.qq.com/"},
                               timeout=15)
                response.raise_for_status()
                text = response.content.decode("gbk", errors="replace")
                valid = {}
                for line in text.split(";"):
                    if not line.strip():
                        continue
                    try:
                        item = parse_quote(line, day)
                        if item["code"] in batch:
                            valid[item["code"]] = item
                    except ValueError:
                        pass
                if not valid:
                    raise RuntimeError("No quotes verified for requested date")
                results.update(valid)
                break
            except Exception as exc:
                if attempt:
                    LOG.warning("Tencent batch %s failed: %s", n, exc)
                else:
                    time.sleep(1.5)
        time.sleep(0.15)
    coverage = len(results) / len(codes) if codes else 0
    LOG.info("Tencent %d/%d verified (%0.1f%%)", len(results), len(codes), coverage * 100)
    if len(results) < 3000 or coverage < 0.90:
        raise RuntimeError("Incomplete/stale quote universe: %d/%d (%0.1f%%)"
                           % (len(results), len(codes), coverage * 100))
    return sorted(results.values(), key=lambda x: x["code"])

def save_snapshot(data, out=OUT):
    day = data["date"]
    if len(data["stocks"]) < 3000 or data["market"]["turnover_yi"] <= 0:
        raise ValueError("Reject incomplete market data")
    folder = out / "snapshots"
    folder.mkdir(parents=True, exist_ok=True)
    dates = sorted({x.stem for x in folder.glob("????-??-??.json")} | {day})
    index = {"schema_version": 1, "latest_date": dates[-1], "dates": dates,
             "source": "AKShare stock universe + verified Tencent dated stock quotes"}
    def write(path, obj):
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(json.dumps(obj, ensure_ascii=False, allow_nan=False,
                                   separators=(",", ":")) + "\n", encoding="utf-8")
        os.replace(temp, path)
    write(folder / (day + ".json"), data)
    if day == dates[-1]:
        write(out / "latest.json", data)
    write(out / "index.json", index)

def main(now=None):
    import akshare as ak
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    now = (now or datetime.now(TZ)).astimezone(TZ)
    day = now.date().isoformat()
    if now.hour < 15 or (now.hour == 15 and now.minute < 20):
        LOG.info("Before Shanghai 15:20; no closing snapshot yet")
        return
    calendar = ak.tool_trade_date_hist_sina()
    if "trade_date" not in calendar.columns:
        raise RuntimeError("Trade calendar schema changed")
    calendar_dates = {str(x)[:10] for x in calendar["trade_date"]}
    if not calendar_dates:
        raise RuntimeError("Empty trading calendar")
    if day not in calendar_dates:
        LOG.info("Market closed on %s; last real snapshot preserved", day)
        return
    codes, source = discover_codes(ak)
    stocks = fetch_quotes(codes, day)
    amount = round(sum(x["turnover_yi"] for x in stocks), 4)
    payload = {
        "schema_version": 1, "date": day,
        "market": {
            "turnover_yi": amount,
            "scope": "沪深A股股票有效行情（含科创板；不含北交所/ETF；不含停牌、无有效行情者）"
        },
        "sectors": [], "stocks": stocks,
        "quality": {
            "status": "partial", "coverage_pct": round(len(stocks) / len(codes) * 100, 2),
            "message": "沪深A股股票成交额、收盘价有日期核验；行业及主力资金数据待核。"
        },
        "data_sources": [
            {"provider": "AKShare", "api": source, "role": "发现沪深A股股票代码"},
            {"provider": "Tencent", "api": "qt.gtimg.cn", "role": "逐股核验2026交易日及行情"}
        ]
    }
    save_snapshot(payload)
    LOG.info("PUBLISHED %s, %d stocks, %0.2f 亿元", day, len(stocks), amount)

if __name__ == "__main__":
    main()
