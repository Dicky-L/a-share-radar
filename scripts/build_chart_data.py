"""Generate small, auditable market chart summaries from archived, REAL dated snapshots.

Only source: data/snapshots/YYYY-MM-DD.json.
Never backfill missing numbers or mix data with a report's original publication.
"""
from __future__ import annotations

import json
import math
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOTS = ROOT / "data" / "snapshots"
OUTPUT = ROOT / "data" / "market-history.json"
DATE_FILENAME = re.compile(r"^\d{4}-\d{2}-\d{2}\.json$")


def finite(value):
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def summarize(path: Path) -> dict:
    if not DATE_FILENAME.fullmatch(path.name):
        raise ValueError("Not a dated snapshot")
    report_date = path.stem
    date.fromisoformat(report_date)
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("date") != report_date:
        raise ValueError(f"Date conflict in {path.name}")
    stocks = data.get("stocks")
    market = data.get("market")
    if not isinstance(stocks, list) or len(stocks) < 3000 or not isinstance(market, dict):
        raise ValueError(f"Insufficient archived data in {path.name}")
    total = finite(market.get("turnover_yi"))
    if total is None or total <= 0 or not market.get("scope"):
        raise ValueError(f"Missing market scope/total in {path.name}")

    amounts = []
    changes = []
    top = []
    for row in stocks:
        if not isinstance(row, dict) or not re.fullmatch(r"\d{6}", str(row.get("code", ""))):
            raise ValueError(f"Invalid stock record in {path.name}")
        value = finite(row.get("turnover_yi"))
        if value is None or value < 0:
            raise ValueError(f"Invalid turnover in {path.name}")
        amounts.append(value)
        pct = finite(row.get("change_pct"))
        if pct is not None:
            changes.append(pct)
        top.append({
            "code": row["code"], "name": str(row.get("name") or "")[:40],
            "turnover_yi": round(value, 4),
            "change_pct": round(pct, 4) if pct is not None else None,
        })
    if abs(sum(amounts) - total) > max(0.5, total * 0.0002):
        raise ValueError(f"Total turnover does not match sum of stocks in {path.name}")
    # No presumption of an exchange-published whole-market total; preserved provider scope.
    up = sum(1 for x in changes if x > 0)
    down = sum(1 for x in changes if x < 0)
    flat = sum(1 for x in changes if x == 0)
    if up + down + flat != len(changes):
        raise ValueError("Price breadth buckets do not sum to verified observations")
    coverage = finite((data.get("quality") or {}).get("coverage_pct"))
    if coverage is not None and not 0 <= coverage <= 100:
        raise ValueError("Bad coverage")

    normalized_sectors = []
    for row in data.get("sectors") or []:
        name = str(row.get("name") or "")
        turnover = finite(row.get("turnover_yi"))
        net = finite(row.get("net_yi"))
        if not name or turnover is None or turnover < 0:
            continue
        normalized_sectors.append({
            "name": name,
            "turnover_yi": round(turnover, 4),
            "net_yi": round(net, 4) if net is not None else None,
            "net_strength_pct": round(100 * net / turnover, 4) if net is not None and turnover > 0 else None,
            "buy_yi": finite(row.get("buy_yi")),
            "sell_yi": finite(row.get("sell_yi")),
            "classification": str(row.get("classification") or ""),
        })
    return {
        "date": report_date,
        "market_turnover_yi": round(total, 4),
        "scope": market["scope"],
        "stock_count": len(stocks),
        "valid_change_count": len(changes),
        "breadth": {"up": up, "down": down, "flat": flat, "missing": len(stocks) - len(changes)},
        "top_turnover": sorted(top, key=lambda x: x["turnover_yi"], reverse=True)[:10],
        "sectors": normalized_sectors,
        "coverage_pct": coverage,
        "quality_status": (data.get("quality") or {}).get("status", "unknown"),
        "source": "归档股票快照 data/snapshots/" + report_date + ".json",
        "data_sources": data.get("data_sources") or [],
    }


def build(folder=SNAPSHOTS) -> dict:
    history = [summarize(p) for p in sorted(folder.glob("????-??-??.json"))]
    days = [r["date"] for r in history]
    if len(days) != len(set(days)):
        raise ValueError("Duplicate dates in history")
    return {
        "schema_version": 1,
        "description": "真实行情快照衍生统计，不能视为ChatGPT当天归档报告原始内容。",
        "days": history,
    }


def main():
    result = build()
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print("Compiled %d verified snapshot dates: %s" % (len(result["days"]), ",".join(x["date"] for x in result["days"])))


if __name__ == "__main__":
    main()
