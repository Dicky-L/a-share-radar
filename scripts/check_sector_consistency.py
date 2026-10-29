"""Validate the canonical Shenwan L1 net-flow time series, across reports.

Only the designated primary series (STCN/Databao) can contribute to the
double-date comparison. Secondary vendors may be cited separately, but never
silently mixed into the primary sector table. Fail CI on conflicts.
"""
from __future__ import annotations
import json
import re
from datetime import date
from decimal import Decimal
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
STORE=ROOT/"data"/"industry-flows"
REPORTS=ROOT/"reports"
FAMILY="stcn_databao_sw1_mainflow"
HEADINGS=re.compile(r"10月(\d{1,2})日主力净额")
REPORT_DATES=("2026-10-26","2026-10-27","2026-10-28","2026-10-29")


def decimal(raw):
    content=raw.replace("**","").replace(",","").replace("−","-").replace("亿元","").strip()
    if content in ("待核","待验证","—","–","-",""):return None
    return Decimal(content.replace("+",""))


def canonical(store=STORE):
    result={}
    for path in sorted(Path(store).glob("*.json")):
        doc=json.loads(path.read_text(encoding="utf-8"))
        day=doc.get("date")
        if day!=path.stem or date.fromisoformat(day).isoformat()!=day:
            raise ValueError(f"canonical date mismatch: {path}")
        if doc.get("source_id")!=FAMILY or doc.get("industry_classification")!="申万一级":
            raise ValueError(f"incompatible primary fund provider: {path}")
        if doc.get("unit")!="亿元":
            raise ValueError(f"unapproved unit: {path}")
        if not doc.get("source_url") or not doc.get("published_at"):
            raise ValueError(f"missing as-of source provenance: {path}")
        values={}
        for row in doc.get("industries",[]):
            name=row["name"]
            number=Decimal(str(row["net_yi"]))
            if name in values:raise ValueError(f"duplicate industry {day}/{name}")
            values[name]=number
        if not values:raise ValueError(f"no sector data: {path}")
        if doc.get("full_31_industries") and len(values)!=31:
            raise ValueError(f"incomplete 31-industry source: {path}")
        result[day]=values
    return result


def table_in_report(report):
    m=re.search(r"^## 三、10个申万一级行业双日对照[^\n]*$",report,re.M)
    if not m:raise ValueError("missing primary industry section")
    end=re.search(r"^## 四、",report[m.end():],re.M)
    section=report[m.end():m.end()+end.start()] if end else report[m.end():]
    lines=section.splitlines()
    i=next((i for i,line in enumerate(lines) if line.startswith("|") and "申万一级行业" in line and "主力净额" in line),None)
    if i is None:raise ValueError("missing dated funding table headers")
    header=[x.strip() for x in lines[i].strip("|").split("|")]
    days=[]
    for col in header[1:3]:
        found=HEADINGS.search(col)
        if not found:raise ValueError("industry table heading has no exact trade dates: "+col)
        days.append("2026-10-"+found.group(1).zfill(2))
    if len(set(days))!=2 or days[0]>=days[1]:
        raise ValueError("industry table trade days out of order")
    if i+1>=len(lines) or not re.match(r"^\|\s*-",lines[i+1]):
        raise ValueError("industry table separators missing")
    rows=[]
    for line in lines[i+2:]:
        if not line.startswith("|"):break
        columns=[x.strip() for x in line.strip("|").split("|")]
        if len(columns)<4:raise ValueError("industry table row missing price/flow columns")
        rows.append((columns[0],decimal(columns[1]),decimal(columns[2]),decimal(columns[3])))
    if len(rows)!=10:raise ValueError("primary table must contain exactly 10 industries")
    if len(set(x[0] for x in rows))!=10:raise ValueError("industry row duplicated")
    return days,rows,section


def verify(reports=REPORTS,store=STORE):
    truth=canonical(store)
    cross_occurrences={}
    for day in REPORT_DATES:
        report=(Path(reports)/(day+".md")).read_text(encoding="utf-8")
        days,rows,section=table_in_report(report)
        if days[1]!=day:raise ValueError("incorrect right date in "+day)
        if "数据宝" not in section:raise ValueError("provider not disclosed: "+day)
        for name,left,right,change in rows:
            for d,value in zip(days,(left,right)):
                if value is None:continue
                if d not in truth or name not in truth[d]:
                    raise ValueError(f"canonical date-industry value missing: {day} references {d}/{name}")
                expected=truth[d][name]
                if value!=expected:
                    raise ValueError(f"PRIMARY FLOW MISMATCH {day} references {d}/{name}: table={value}, canonical={expected}")
                cross_occurrences.setdefault((d,name),[]).append((day,value))
            if left is None or right is None:
                if change is not None:raise ValueError(f"cannot calculate missing date delta for {day}/{name}")
            elif change !=right-left:
                raise ValueError(f"bad two-day delta {day}/{name}: {change} vs {right-left}")
    # Every repeated trade-date sector has one and only one primary number.
    for key,occurrences in cross_occurrences.items():
        if len({value for _,value in occurrences})>1:
            raise ValueError("CROSS REPORT INCONSISTENCY "+str(key))
    assert truth["2026-10-27"]["电子"]==Decimal("-122.32")
    assert truth["2026-10-28"]["电子"]==Decimal("143.98")
    return cross_occurrences


if __name__=="__main__":
    observations=verify()
    print(f"PASS: {len(observations)} unique date+industry observations and consistent cross-day canonical flows.")
