"""Verify a Beijing-day stock report's V1 publication contract.

This checks structure only, not source truth or trading profitability.
"""
from __future__ import annotations
import argparse
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
INDUSTRIES = (
    "电子", "通信", "计算机", "传媒", "汽车", "机械设备", "国防军工",
    "电力设备", "银行", "公用事业", "石油石化", "基础化工", "有色金属",
    "煤炭", "钢铁", "建筑材料", "建筑装饰", "房地产", "农林牧渔",
    "食品饮料", "家用电器", "纺织服饰", "轻工制造", "医药生物",
    "商贸零售", "社会服务", "交通运输", "环保", "美容护理",
    "非银金融", "综合",
)
REQUIRED = (
    ("选股结论", r"选股结论"),
    ("全市场资金总览", r"(全市场资金|市场.*总览)"),
    ("10个申万一级行业双日对照", r"(10个申万|十个申万|行业双日对照)"),
    ("资金关注度与产业解读", r"(产业解读|资金关注度)"),
    ("选股观察与卖出计划", r"(选股观察.*卖出|卖出计划)"),
    ("前期推荐与失败复盘", r"(失败复盘|前期推荐)"),
    ("仓位与卖出风险管理", r"(风险管理|仓位与卖出)"),
    ("下一交易日验证清单", r"(验证清单|下一交易日)"),
    ("数据口径、来源与局限", r"(数据口径|来源与局限)"),
)

def china_date():
    return datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat()

def verify(day: str, folder: Path = REPORTS):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
        return False, "Invalid report date"
    path = folder / (day + ".md")
    if not path.is_file():
        return False, f"{path}: report file missing"
    doc = path.read_text(encoding="utf-8")
    m = re.match(r"\A---\n(.*?)\n---\n(.*)\Z", doc, re.S)
    if not m:
        return False, f"{path}: invalid frontmatter"
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    if meta.get("date") != day:
        return False, f"{path}: wrong publication date"
    if meta.get("status") != "original":
        return False, f"{path}: not an original full report (status={meta.get('status')})"
    if meta.get("report_type") == "historical_reconstruction":
        return False, f"{path}: retrospective reconstruction cannot count as original"
    if not meta.get("source") or not meta.get("title"):
        return False, f"{path}: missing title/source metadata"
    body = m.group(2)
    if len(body.strip()) < 1200:
        return False, f"{path}: report too short"
    headings = list(re.finditer(r"^##\s+(.+)$", body, re.M))
    found = []
    for heading in headings:
        for name, pattern in REQUIRED:
            if re.search(pattern, heading.group(1)) and name not in found:
                found.append(name)
                break
    if found != [name for name, _ in REQUIRED]:
        return False, f"{path}: V1 headings missing/out of order: {found}"
    sector_i = next(i for i, h in enumerate(headings) if re.search(REQUIRED[2][1], h.group(1)))
    start = headings[sector_i].end()
    end = headings[sector_i + 1].start() if sector_i + 1 < len(headings) else len(body)
    sector_text = body[start:end]
    rows = [x.strip() for x in sector_text.splitlines() if x.lstrip().startswith("|") and x.rstrip().endswith("|")]
    if not rows or "行业" not in rows[0] or "净额" not in rows[0]:
        return False, f"{path}: sector comparison table/header missing"
    actual = []
    for row in rows[1:]:
        cell = row.strip("|").split("|", 1)[0].strip().replace("**", "")
        if cell in INDUSTRIES:
            actual.append(cell)
    if len(actual) != 10 or len(set(actual)) != 10:
        return False, f"{path}: expected 10 distinct sector rows, got {len(actual)}"
    if not re.search(r"https?://", body):
        return False, f"{path}: source hyperlinks missing"
    return True, f"{path}: passes structural V1 verification (not a truth/market data audit)"

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--date", default=china_date())
    p.add_argument("--reports-dir", type=Path, default=REPORTS)
    args = p.parse_args()
    ok, message = verify(args.date, args.reports_dir)
    print(("PASS: " if ok else "NOT PUBLISHED: ") + message)
    print("Website: https://dicky-l.github.io/a-share-radar/?date=" + args.date)
    if not ok:
        print("This check cannot create reports or send alerts. Inspect task run and connector permissions.")
        raise SystemExit(1)

if __name__ == "__main__":
    main()
