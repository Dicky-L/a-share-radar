"""Extract the stock-selection journal from ACTUAL dated report tables.

This is NOT an automatic stock screener or trade execution tool.
Missing triggers, invalidation and exits stay absent; never invent trading positions.
"""
from __future__ import annotations
import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
DEST = REPORTS / "candidates.json"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\.md$")
TICKER_RE = re.compile(r"(?<!\d)(?:60|00|30)\d{4}(?!\d)")

def cells(line: str):
    return [v.strip() for v in line.strip().strip("|").split("|")]

def plain(text: str):
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    return re.sub(r"[*_\x60]", "", text).strip()

def col(headers, values, patterns):
    for i, name in enumerate(headers):
        if any(key in name for key in patterns):
            return plain(values[i]) if i < len(values) else ""
    return ""

def extract(text: str, day: str, status: str):
    date.fromisoformat(day)
    section = ""
    result = []
    seen = set()
    lines = text.replace("\r", "").splitlines()
    for i, line in enumerate(lines):
        head = re.match(r"^#{2,3}\s+(.+)$", line.strip())
        if head:
            section = plain(head.group(1))
        # One narrow form is supported for older summaries where an explicit B-pool
        # roster was written in prose. Do NOT infer a pool from general discussion.
        if section in {"候选池", "观察候选"} and not line.strip().startswith("|"):
            named_pool = re.search(r"([ABC])池观察股", line, re.I)
            if named_pool:
                for raw_name, ticker in re.findall(r"([\u4e00-\u9fff]{2,12})（((?:60|00|30)\d{4})）", line):
                    name = raw_name.removeprefix("保留")
                    if not name or (day,ticker,"watchlist") in seen:
                        continue
                    seen.add((day,ticker,"watchlist"))
                    result.append({
                        "date":day,"code":ticker,"name":name,"pool":named_pool.group(1).upper(),
                        "role":"watchlist","section":section,"reason":None,
                        "entry_trigger":None,"no_chase":None,"invalidation":None,
                        "exit_plan":None,"risk":None,"report_status":status,
                        "source_file":"./reports/"+day+".md",
                    })
        # Dated original reports may describe a candidate in a bold prose
        # headline (e.g. "**B池：生益科技（600183，电子...）**").
        # Only an explicit pool + ticker qualifies; never infer retrospectively.
        prose_match = re.search(
            r"([ABC])池[:：]\\s*([\\u4e00-\\u9fff]{2,12})[（(]((?:60|00|30)\\d{4})[，,)）]",
            line, re.I
        )
        if prose_match:
            pool, name, ticker = prose_match.group(1).upper(), prose_match.group(2), prose_match.group(3)
            key = (day,ticker,"watchlist")
            if key not in seen:
                seen.add(key)
                result.append({
                    "date":day, "code":ticker, "name":name, "pool":pool,
                    "role":"watchlist", "section":section,
                    "reason":None, "entry_trigger":None, "no_chase":None,
                    "invalidation":None, "exit_plan":None, "risk":None,
                    "report_status":status,
                    "source_file":"./reports/"+day+".md",
                })
        if not line.strip().startswith("|") or i+2 >= len(lines):
            continue
        headers = [plain(x) for x in cells(line)]
        if not any("代码" in x for x in headers) or not any(
            ("股票" in x or "标的" in x or "名称" in x or "公司" in x) for x in headers
        ):
            continue
        if not re.fullmatch(r"[|:\-\s]+", lines[i+1].strip()):
            continue
        role = (
            "historical_review" if any(x in section for x in ("验证", "复盘", "历史", "回测", "持仓"))
            else "watchlist"
        )
        j = i+2
        while j < len(lines) and lines[j].strip().startswith("|"):
            vals = cells(lines[j])
            found = TICKER_RE.search(col(headers, vals, ("代码",)))
            if not found:
                j += 1
                continue
            ticker = found.group(0)
            name = col(headers, vals, ("股票", "标的", "名称", "公司"))
            if not name:
                j += 1
                continue
            pool_raw = col(headers, vals, ("池别", "池", "类别", "等级"))
            pool_match = re.search(r"(?<![a-zA-Z])([ABC])\s*(?:池|级|候选)?(?![a-zA-Z])", pool_raw, re.I)
            pool = pool_match.group(1).upper() if pool_match else None
            original_reason = col(headers, vals, ("观察逻辑", "观察思路", "理由", "分析", "逻辑", "依据"))
            if not original_reason:
                tagged_reason = col(headers, vals, ("观察类别",))
                original_reason = re.sub(r"^[ABC]池[,，\\s]*", "", tagged_reason) if tagged_reason else ""
            trigger = col(headers, vals, ("入场条件", "买入条件", "买入触发", "验证条件", "触发条件"))
            avoid = col(headers, vals, ("不追高", "禁止追高", "追高限制"))
            invalidation = col(headers, vals, ("失效", "止损"))
            exit_plan = col(headers, vals, ("卖出", "止盈", "退出"))
            risk = col(headers, vals, ("风险", "拥挤"))
            row = (day, ticker, role)
            if row not in seen:
                seen.add(row)
                result.append({
                    "date":day, "code":ticker, "name":name, "pool":pool,
                    "role":role, "section":section,
                    "reason":original_reason or None,
                    "entry_trigger":trigger or None,
                    "no_chase":avoid or None,
                    "invalidation":invalidation or None,
                    "exit_plan":exit_plan or None,
                    "risk":risk or None,
                    "report_status":status,
                    "source_file":"./reports/"+day+".md",
                })
            j += 1
    return result

def build(folder=REPORTS):
    entries = []
    for path in sorted(folder.glob("????-??-??.md")):
        if not DATE_RE.fullmatch(path.name):
            raise ValueError("Invalid report name: "+path.name)
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            raise ValueError("Missing metadata: "+path.name)
        parts = text.split("---\n",2)
        if len(parts) != 3:
            raise ValueError("Malformed metadata: "+path.name)
        fields = {}
        for line in parts[1].splitlines():
            if ":" in line:
                k,v = line.split(":",1)
                fields[k.strip()] = v.strip()
        if fields.get("date") != path.stem:
            raise ValueError("Report/date mismatch: "+path.name)
        status = fields.get("status")
        if status not in {"original","summary"}:
            raise ValueError("Invalid report provenance: "+path.name)
        entries += extract(parts[2],path.stem,status)
    # Recover only explicitly documented prior-task fields. Never re-label
    # these supplementary notes as a complete original report.
    details_path = folder / "recovered-details.json"
    if details_path.exists():
        supplement = json.loads(details_path.read_text(encoding="utf-8"))
        if supplement.get("schema_version") != 1 or not isinstance(supplement.get("items"), list):
            raise ValueError("Recovered details index invalid")
        existing = {(row["date"],row["code"],row["role"]):row for row in entries}
        seen_supplements = set()
        for note in supplement["items"]:
            day,code = note.get("date"),note.get("code")
            if not isinstance(day,str) or not DATE_RE.fullmatch(day+".md") or not isinstance(code,str) or not TICKER_RE.fullmatch(code):
                raise ValueError("Bad documented stock detail key")
            key = (day,code,"watchlist")
            if key in seen_supplements:
                raise ValueError("Duplicate historical details "+str(key))
            seen_supplements.add(key)
            row = existing.get(key)
            if not row:
                raise ValueError("Supplement has no matching archived watchlist "+str(key))
            for field in ("reason","entry_trigger","no_chase","invalidation","exit_plan","risk"):
                value = note.get(field)
                if value is None:continue
                if not isinstance(value,str) or not value.strip():
                    raise ValueError("Empty/non-text recovered detail "+field)
                original = row.get(field)
                if original and original != value:
                    row[field] = original+"；补充：" + value if field=="reason" else original+"；历史推送补充："+value
                else:
                    row[field] = value
            row["supplement_source"] = note.get("provenance","此前推送记录可检索摘要（非原始全文）")
    history = {}
    for row in entries:
        key = row["code"]
        history.setdefault(key,{"code":key,"name":row["name"],"observations":[]})
        history[key]["observations"].append({
            "date":row["date"],"pool":row["pool"],"role":row["role"],"report_status":row["report_status"]
        })
    return {
        "schema_version":1,
        "extraction":"Only explicit dated Markdown stock tables; no inference of buys, sells, success or omissions.",
        "records":entries,
        "stocks":list(history.values()),
    }

def main():
    d = build()
    DEST.write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print("Extracted %d dated stock records across %d tickers" % (len(d["records"]),len(d["stocks"])))

if __name__=="__main__":
    main()
