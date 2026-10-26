"""将已提交的 reports/YYYY-MM-DD.md 编译为可搜索的 GitHub Pages 日报目录。"""
from __future__ import annotations
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "reports"
DATE_FILE = re.compile(r"^\d{4}-\d{2}-\d{2}\.md$")


def parse_markdown(path: Path):
    text = path.read_text(encoding="utf-8")
    match = DATE_FILE.fullmatch(path.name)
    if not match:
        raise ValueError(f"Invalid report filename: {path.name}")
    report_date = path.stem
    if date.fromisoformat(report_date).isoformat() != report_date:
        raise ValueError(f"Invalid date: {report_date}")
    if not text.startswith("---\n"):
        raise ValueError(f"Missing YAML-style metadata: {path.name}")
    parts = text.split("---\n", 2)
    if len(parts) != 3:
        raise ValueError(f"Unclosed metadata block: {path.name}")
    meta = {}
    for line in parts[1].splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        meta[k.strip()] = v.strip().strip('"').strip("'")
    if meta.get("date") != report_date:
        raise ValueError(f"Date mismatch: {path.name}")
    if meta.get("status") not in {"original", "summary"}:
        raise ValueError(f"Invalid status: {path.name}")
    body = parts[2].strip()
    if not body:
        raise ValueError(f"Empty report: {path.name}")
    title = meta.get("title") or f"A股启动与卖出雷达｜{report_date}"
    preview = meta.get("preview") or body[:90].replace("\n", " ")
    return {
        "date": report_date,
        "title": title,
        "preview": preview,
        "status": meta["status"],
        "report_type": meta.get("report_type", "dated_report_archive"),
        "reconstructed_at": meta.get("reconstructed_at"),
        "source": meta.get("source", "日报归档"),
        "file": "./reports/" + path.name,
        "search_text": (title + " " + preview + " " + body)[:40000],
    }


def build(folder=FOLDER):
    items = [parse_markdown(path) for path in sorted(folder.glob("????-??-??.md"), reverse=True)]
    if len({x["date"] for x in items}) != len(items):
        raise ValueError("Duplicate report dates")
    return {
        "version": 1,
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "count": len(items),
        "items": items,
    }


def main():
    FOLDER.mkdir(parents=True, exist_ok=True)
    payload = build()
    output = FOLDER / "index.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Compiled {payload['count']} radar reports; newest: {payload['items'][0]['date'] if payload['items'] else 'none'}")


if __name__ == "__main__":
    main()
