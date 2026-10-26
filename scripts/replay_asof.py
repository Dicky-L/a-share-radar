"""Point-in-time historical replay of the verifiable PRICE/VOLUME SUBSET only.

Selection reads <= signal day. Future outcomes are calculated by a separate
function after frozen selections are constructed. DOES NOT reproduce full
L1-L4 strategy: no 20/60-day history, sector cash flow, disclosure vintages,
actual buy-trigger fill, actual P&L or live historical recommendations.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_INDEX = ROOT / "data" / "index.json"
SOURCE_SNAPSHOTS = ROOT / "data" / "snapshots"
OUTPUT = ROOT / "replay" / "asof"
FROZEN = OUTPUT / "frozen-selections.json"
UNIVERSE = re.compile(r"^(?:60|00|30)\d{4}$")
STOP_DATE = "2026-10-22"
MIN_SESSIONS = 6
MAX_PICKS = 10
POLICY_ID = "l1-l2-price-turnover-proxy-2026-10-v1"


def valid_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def get_dates(index_path=SOURCE_INDEX):
    doc = json.loads(Path(index_path).read_text(encoding="utf-8"))
    dates = doc.get("dates")
    if not isinstance(dates, list) or not dates:
        raise ValueError("Empty historical-date index")
    if sorted(set(dates)) != dates:
        raise ValueError("Date index must be sorted and unique")
    for day in dates:
        if date.fromisoformat(day).isoformat() != day:
            raise ValueError("Invalid date in index " + day)
    return dates


def load_snapshot(day, asof, directory=SOURCE_SNAPSHOTS):
    """A hard access guard: even a coding mistake cannot read later prices."""
    if day > asof:
        raise ValueError(f"LOOKAHEAD BLOCKED: requested {day}, asof is {asof}")
    path = Path(directory) / (day + ".json")
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("date") != day or not isinstance(doc.get("stocks"), list):
        raise ValueError("Dated snapshot mismatch " + day)
    if len(doc["stocks"]) < 3000:
        raise ValueError("Suspicious incomplete snapshot " + day)
    stocks = {}
    for stock in doc["stocks"]:
        code = str(stock.get("code", ""))
        if not UNIVERSE.fullmatch(code):
            continue
        close, turnover = stock.get("price"), stock.get("turnover_yi")
        change_pct = stock.get("change_pct")
        if not valid_number(close) or close <= 0 or not valid_number(turnover) or turnover < 0:
            continue
        if change_pct is not None and not valid_number(change_pct):
            continue
        name = str(stock.get("name", "")).strip()
        if not name or re.search(r"(?i)(?:\*?ST|退市|退$)", name):
            continue
        if code in stocks:
            raise ValueError("Duplicate ticker " + day + " " + code)
        stocks[code] = {"code": code, "name": name, "close": float(close),
                        "turnover": float(turnover), "day_change": change_pct}
    if len(stocks) < 2500:
        raise ValueError("Too few admissible ticker quotes for " + day)
    return {"date": day, "stocks": stocks, "market": doc.get("market", {}),
            "source": doc.get("data_sources", []),
            "quality": doc.get("quality", {})}


def pct(value, baseline):
    return round((value / baseline - 1.0) * 100, 3) if baseline and value is not None else None


def screen(asof, dates, loader=load_snapshot):
    """Only L1/L2 proxy. Never call with dates beyond asof or future annotations."""
    allowed = [d for d in dates if d <= asof]
    if not allowed or allowed[-1] != asof:
        raise ValueError("As-of day missing from supplied market dates")
    # Enforce chronology at each access, not just in the orchestration layer.
    snapshots = [loader(d, asof) for d in allowed[-MIN_SESSIONS:]]
    current = snapshots[-1]
    stocks = current["stocks"]
    n_up = sum(1 for r in stocks.values() if valid_number(r["day_change"]) and r["day_change"] > 0)
    n_down = sum(1 for r in stocks.values() if valid_number(r["day_change"]) and r["day_change"] < 0)
    breadth = n_up / max(1, n_up + n_down)
    # Existing original strategy permits no entry after widespread selling.
    weak_market = breadth < 0.25
    result = {
        "date": asof, "policy_id": POLICY_ID,
        "report_type": "partial_pit_replay",
        "asof_date": asof, "data_access_ceiling": asof,
        "selection_status": "partial_l1_l2_only_not_original_strategy",
        "market": {
            "up": n_up, "down": n_down, "up_share": round(breadth * 100, 2),
            "weak_breadth": weak_market,
            "turnover_yi": current["market"].get("turnover_yi"),
            "scope": current["market"].get("scope", ""),
        },
        "evidence": {
            "L1_market_breadth": True,
            "L2_5_session_close_and_turnover": len(snapshots) >= MIN_SESSIONS,
            "L2_20_day_price_history": len(allowed) >= 20,
            "L2_60_day_price_history": len(allowed) >= 60,
            "L3_sector_flow_and_vintaged_catalysts": False,
            "L4_vintaged_financial_risk_review": False,
            "exchange_universe_asof_verified": False,
        },
        "pool_A": [], "pool_B_provisional": [], "pool_C_risk_only": [],
        "signals": [],
        "limitations": [
            "不是原L1-L4全量选股回测，只是可用历史收盘与成交额的量价预筛。",
            "无法验证历史当日发布的消息/财报时，不推断催化和治理风险，不产生A池正式信号。",
            "数据库股票名录及证券简称可能经过事后回填，存在幸存者偏差；无完整复权/OHLC。",
            "未验证次日盘中可成交价格，任何收盘收益均不是实盘净利润。",
        ],
    }
    if len(snapshots) < MIN_SESSIONS:
        result["selection_status"] = "warmup_insufficient_history"
        return result
    if weak_market:
        result["selection_status"] = "market_breadth_too_weak_no_new_entry"
        return result
    historical = [s["stocks"] for s in snapshots]
    eligible = set.intersection(*[set(m) for m in historical])
    pool = []
    for code in eligible:
        series = [m[code] for m in historical]
        latest = series[-1]
        base = series[0]["close"]
        close = latest["close"]
        five_day_ret = pct(close, base)
        daily = latest["day_change"]
        # Strictly contemporaneous volume/turnover proxies, not retroactive
        # labels learned from next-day winners.
        prev_amount = sum(r["turnover"] for r in series[-4:-1]) / 3
        turnover_ratio = latest["turnover"] / prev_amount if prev_amount > 0 else 0
        previous_high = max(r["close"] for r in series[:-1])
        peak_5d = max(r["close"] for r in series)
        if any([
            close < 3.0,
            latest["turnover"] < 1.0,  # billion? amounts here are 100m CNY units.
            not valid_number(daily),
            daily < 0.5 or daily > 6.0,
            five_day_ret is None or five_day_ret < 1.5 or five_day_ret > 12.0,
            turnover_ratio < 1.25 or turnover_ratio > 4.0,
            close <= previous_high,
        ]):
            continue
        # The following are explicit experimental entry WATCH conditions, not
        # previously published prices and not verified support/resistance.
        trigger = round(close * 1.01 + 0.00001, 2)
        prior_median = sorted(r["close"] for r in series[-5:])[2]
        score = (min(turnover_ratio, 3.0) - 1) * 1.5 + five_day_ret / 9 + max(0, daily) / 8
        pool.append({
            "date": asof, "code": code, "name": latest["name"],
            "pool": "B", "classification": "TECHNICAL_PRESCREEN_ONLY",
            "reference_close": close,
            "reference_type": "当日已收盘观测价，非实际入场价",
            "daily_change_pct": round(daily, 3),
            "price_change_5_sessions_pct": five_day_ret,
            "turnover_yi": round(latest["turnover"], 4),
            "turnover_ratio_prev3": round(turnover_ratio, 3),
            "selection_score": round(score, 4),
            "selection_reason": "五交易日收盘创新高、价格温和上行、当日成交额相对前三日均值放大；仅技术预筛。",
            "entry_condition": f"下一交易日收盘价达到或高于 {trigger:.2f} 元，且成交额不少于信号日80%；信号当日不能事先成交。",
            "entry_price_observation": trigger,
            "invalid_condition": f"收盘跌破近5日收盘中位参考 {prior_median:.2f} 元时撤销预筛观察（不是盘中止损单）。",
            "sell_plan": "没有可验证实际成交价；如未来确实满足入场且可成交，5%/8%分批目标和失效/时间退出仅作未经回测的情景模板。",
            "fundamental_status": "未验证截至当日的财报、公告、催化，不允许升级为正式推荐。",
            "not_actual_recommendation": True,
        })
    pool.sort(key=lambda r: (-r["selection_score"], r["code"]))
    picked = pool[:MAX_PICKS]
    result["pool_B_provisional"] = picked
    result["signals"] = picked
    return result


def freeze_selections(dates, end=STOP_DATE, loader=load_snapshot):
    """Call selector with only <= d dates; future data never passed to selector."""
    prepared = []
    for day in dates:
        if day > end:
            break
        prepared.append(screen(day, [d for d in dates if d <= day], loader))
    return prepared


def evaluate(frozen, dates, snapshot_loader):
    """Independent second pass, after immutable selection list exists."""
    selected_dates = {r["date"] for r in frozen}
    if not selected_dates:
        return []
    quotes = {}
    for d in dates:
        # In evaluation we are allowed to read later prices up to available end.
        obj = snapshot_loader(d, d)
        quotes[d] = obj["stocks"]
    # Comparison is evaluated AFTER signal selection, against a same-date
    # equal-weight sample. This is only a stock-level direction benchmark,
    # not an official equity index and not an executable market portfolio.
    benchmark = {}
    for report in frozen:
        base_day = report["date"]
        base_stocks = quotes.get(base_day, {})
        for future_day in (d for d in dates if d > base_day):
            next_stocks = quotes[future_day]
            changes = []
            for code, row in base_stocks.items():
                next_row = next_stocks.get(code)
                if next_row and row["close"] > 0:
                    changes.append((next_row["close"] / row["close"] - 1) * 100)
            benchmark[(base_day, future_day)] = round(
                sum(changes) / len(changes), 3
            ) if len(changes) >= 2500 else None
    outcomes = []
    for report in frozen:
        if report["selection_status"] not in {"partial_l1_l2_only_not_original_strategy"}:
            continue
        day = report["date"]
        future = [d for d in dates if d > day]
        for signal in report["signals"]:
            later = []
            for i, fday in enumerate(future):
                stock = quotes[fday].get(signal["code"])
                c = stock["close"] if stock else None
                raw_return = pct(c, signal["reference_close"])
                matched_benchmark = benchmark.get((day, fday))
                later.append({
                    "trading_day": i + 1, "date": fday, "close": c,
                    "return_pct": raw_return,
                    "market_equal_weight_pct": matched_benchmark,
                    "excess_over_equal_weight_pct": round(
                        raw_return - matched_benchmark, 3
                    ) if raw_return is not None and matched_benchmark is not None else None,
                })
            checkpoints = {("d" + str(n)): later[n - 1] if len(later) >= n else None
                           for n in (1, 3, 5, 10)}
            outcomes.append({
                "date": day, "code": signal["code"], "name": signal["name"],
                "pool": "B", "classification": "TECHNICAL_PRESCREEN_ONLY",
                "reference_close": signal["reference_close"],
                "entry_was_executed": None, "realized_return_pct": None,
                "checkpoints": checkpoints, "observations": later,
            })
    return outcomes


def checked_frozen(doc, dates, stop=STOP_DATE):
    """Return the one-time committed selections after integrity checks."""
    if not isinstance(doc, dict) or doc.get("schema_version") != 1:
        raise ValueError("Invalid frozen-selection manifest")
    if doc.get("policy_id") != POLICY_ID or doc.get("selection_end") != stop:
        raise ValueError("Frozen policy/version or end date mismatch")
    entries = doc.get("selection")
    if not isinstance(entries, list) or not entries:
        raise ValueError("Frozen selection list is absent")
    frozen_days = [day.get("date") for day in entries]
    if frozen_days != sorted(set(frozen_days)) or frozen_days[-1] != stop:
        raise ValueError("Frozen selection days out of order or incomplete")
    if any(d not in dates or d > stop for d in frozen_days):
        raise ValueError("Frozen dates do not match verified market sources")
    for row in entries:
        day = row["date"]
        if row.get("data_access_ceiling") != day or row.get("asof_date") != day:
            raise ValueError("Frozen selection has inconsistent as-of ceiling")
        if row.get("policy_id") != POLICY_ID or row.get("pool_A"):
            raise ValueError("Frozen selection breaches its technical-only contract")
        for sig in row.get("signals", []):
            if sig.get("date") != day or sig.get("classification") != "TECHNICAL_PRESCREEN_ONLY":
                raise ValueError("Frozen signal has incorrect original date or classification")
    serialized = json.dumps(entries, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    check = hashlib.sha256(serialized).hexdigest()
    if check != doc.get("selection_hash_sha256"):
        raise ValueError("Frozen selection content changed without a new locked baseline")
    return entries


def build(dates, loader=load_snapshot, stop=STOP_DATE, locked_selections=None):
    selections = locked_selections if locked_selections is not None else freeze_selections(dates, end=stop, loader=loader)
    frozen_bytes = json.dumps(selections, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    fingerprint = hashlib.sha256(frozen_bytes).hexdigest()
    # Select first, THEN and only then evaluate against any later observations.
    outcomes = evaluate(selections, dates, loader)
    results = [x for x in outcomes if x["checkpoints"]["d1"] and
               x["checkpoints"]["d1"]["return_pct"] is not None]
    records = sum(len(day["signals"]) for day in selections)
    d1_excess = [x["checkpoints"]["d1"]["excess_over_equal_weight_pct"]
                 for x in outcomes if x["checkpoints"]["d1"] and
                 x["checkpoints"]["d1"]["excess_over_equal_weight_pct"] is not None]
    summary = {
        "evaluated_trade_days": len(selections),
        "technical_prescreen_records": records,
        "distinct_tickers": len({x["code"] for x in outcomes}),
        "d1_observed": len(results),
        "d1_positive": sum(x["checkpoints"]["d1"]["return_pct"] > 0 for x in results),
        "d1_excess_observed": len(d1_excess),
        "d1_excess_positive": sum(v > 0 for v in d1_excess),
        "d1_mean_excess_vs_equal_weight_pct": round(
            sum(d1_excess) / len(d1_excess), 3
        ) if d1_excess else None,
        "d1_mean_close_change_pct": round(
            sum(x["checkpoints"]["d1"]["return_pct"] for x in results) / len(results), 3
        ) if results else None,
        "actual_original_strategy_accuracy": None,
        "actual_executable_profit": None,
        "future_data_not_used_in_selection": True,
    }
    return {
        "schema_version": 1, "policy_id": POLICY_ID,
        "requested_end": stop,
        "market_dates": dates,
        "selection_hash_sha256": fingerprint,
        "selection": selections,
        "results": outcomes,
        "summary": summary,
        "warnings": [
            "技术预筛结果不能称为原L1–L4策略胜率：20/60日、行业资金、财务催化、排雷均不完整。",
            "以日期收盘价计算的D+1变化不是可成交收益；没有成交价格、T+1和手续费验证。",
            "后验回填股票池有幸存者偏差。严禁根据未来价格重排此前日期的候选。",
            "技术预筛阈值在2026-10-26设计，研究者可能在看过历史涨跌后选取规则；即使没有程序层面未来数据泄漏，也不能把这组结果当作独立样本外准确率。",
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--end", default=STOP_DATE)
    parser.add_argument("--output", type=Path, default=OUTPUT / "index.json")
    args = parser.parse_args()
    dates = get_dates()
    if args.end not in dates:
        raise ValueError("Specified replay end must have verified market data")
    if FROZEN.exists():
        manifest = json.loads(FROZEN.read_text(encoding="utf-8"))
        locked = checked_frozen(manifest, dates, stop=args.end)
        result = build(dates, stop=args.end, locked_selections=locked)
        if result["selection_hash_sha256"] != manifest["selection_hash_sha256"]:
            raise ValueError("Published candidate SHA mismatch with frozen manifest")
        result["frozen_at_utc"] = manifest.get("frozen_at_utc")
        result["selection_source"] = "./replay/asof/frozen-selections.json"
        result["historical_selection_is_locked"] = True
    else:
        raise FileNotFoundError("Missing committed replay/asof/frozen-selections.json: publishing mutable history is prohibited")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print("ASOF replay %d days, %d provisional B prescreens, %d D+1 observed, hash %s" % (
        result["summary"]["evaluated_trade_days"],
        result["summary"]["technical_prescreen_records"],
        result["summary"]["d1_observed"],
        result["selection_hash_sha256"][:16]))
    metrics = result["summary"]
    print("D1 PRICE DIRECTION OBSERVED: %d/%d positive; average close-change %s%%" % (
        metrics["d1_positive"], metrics["d1_observed"], metrics["d1_mean_close_change_pct"]))
    print("D1 VS EQUAL-WEIGHT MARKET: %d/%d outperform; mean excess %s percentage points" % (
        metrics["d1_excess_positive"], metrics["d1_excess_observed"],
        metrics["d1_mean_excess_vs_equal_weight_pct"]))
    print("ORIGINAL L1-L4 WIN RATE: NOT MEASURABLE; actual executed P&L: NOT MEASURABLE")


if __name__ == "__main__":
    main()
