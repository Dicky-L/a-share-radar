"""Verify that the primary website has a complete report for its Beijing publication date.

This does not synthesize missing reports and cannot read private ChatGPT task output.
"""
from __future__ import annotations
import argparse
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
REPORTS=ROOT/"reports"

def china_date():
    return datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat()

def verify(day:str,folder:Path=REPORTS):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}",day):
        return False,"Invalid report date"
    path=folder/(day+".md")
    if not path.is_file():
        return False,f"{path}: not published. Scheduled ChatGPT output has not reached the repository."
    doc=path.read_text(encoding="utf-8")
    if not doc.startswith("---\n"):
        return False,f"{path}: no source metadata"
    sections=doc.split("---\n",2)
    if len(sections)!=3:
        return False,f"{path}: unclosed metadata"
    meta={}
    for line in sections[1].splitlines():
        if ":" in line:
            k,v=line.split(":",1)
            meta[k.strip()]=v.strip()
    if meta.get("date")!=day:
        return False,f"{path}: wrong publication date in metadata"
    if meta.get("status")!="original":
        return False,f"{path}: only {meta.get('status','unknown')} version is present, full report is not published"
    body=sections[2].strip()
    if len(body)<700 or len(re.findall(r"^#{1,3}\s+\S+",body,re.M))<3:
        return False,f"{path}: content is too short or lacks the full report's sections"
    if not all(k in body for k in ("市场","股票")):
        return False,f"{path}: missing key report subjects, manual review required"
    # V1 publication contract: a long summary is not a complete nine-section report.
    required=[
        ("选股结论", r"^#{2,3}\\s+.*选股结论"),
        ("市场总览", r"^#{2,3}\\s+.*(?:市场.*总览|全市场资金)"),
        ("十行业双日对照", r"^#{2,3}\\s+.*(?:10个申万|十个申万|行业双日对照)"),
        ("产业解读", r"^#{2,3}\\s+.*(?:产业解读|资金关注度)"),
        ("卖出计划", r"^#{2,3}\\s+.*(?:选股观察.*卖出|卖出计划)"),
        ("失败复盘", r"^#{2,3}\\s+.*(?:失败复盘|前期推荐)"),
        ("风险管理", r"^#{2,3}\\s+.*(?:风险管理|仓位与卖出)"),
        ("下日验证", r"^#{2,3}\\s+.*(?:验证清单|下一交易日)"),
        ("数据来源", r"^#{2,3}\\s+.*(?:数据口径|来源与局限)"),
    ]
    missing=[label for label,pattern in required if not re.search(pattern,body,re.M)]
    if missing:
        return False,f"{path}: missing V1 sections: {', '.join(missing)}"
    if len(re.findall(r"^\\|[^\\n]+\\|\\s*$",body,re.M))<15:
        return False,f"{path}: insufficient sector/stock comparison table rows"
    if not re.search(r"https?://",body):
        return False,f"{path}: no verifiable source links"
    if meta.get("report_type")=="historical_reconstruction":
        return False,f"{path}: reconstructed report cannot be original"
    return True,f"{path}: V1 nine-section original report structurally valid, content length={len(body)}"

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--date",default=china_date())
    p.add_argument("--reports-dir",type=Path,default=REPORTS)
    args=p.parse_args()
    ok,message=verify(args.date,args.reports_dir)
    print(("PASS: " if ok else "NOT PUBLISHED: ")+message)
    print("Website: https://dicky-l.github.io/a-share-radar/?date="+args.date)
    if not ok:
        print("This check cannot publish private ChatGPT output itself. Verify connector write permissions and the scheduled task result.")
        raise SystemExit(1)

if __name__=="__main__":
    main()
