"""Safeguard the versioned daily report layout and 10-industry real data."""
import re
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def industry_table(day):
    text=(ROOT/"reports"/(day+".md")).read_text(encoding="utf-8")
    start=text.find("## ",text.find("\n---\n"))
    sections=list(re.finditer(r"^## (.+)$",text,re.M))
    target=next((m for m in sections if "10个申万一级行业双日对照" in m.group(1)),None)
    if target is None:raise AssertionError("No 10-sector Shenwan comparison for "+day)
    later=next((m for m in sections if m.start()>target.start()),None)
    section=text[target.end():later.start()] if later else text[target.end():]
    lines=section.splitlines()
    header=next(i for i,l in enumerate(lines) if l.startswith("|") and "主力净额" in l and "行业" in l)
    body=[]
    for line in lines[header+2:]:
        if not line.startswith("|"):break
        cols=[x.strip().replace("**","") for x in line.strip("|").split("|")]
        body.append(cols)
    return lines[header],body

def number(v):
    return float(v.replace("+","").replace("−","-").replace("*","").replace(",",""))

class TemplateContracts(unittest.TestCase):
    def test_both_baseline_reports_have_ten_real_industries(self):
        for day in ("2026-10-20","2026-10-23"):
            with self.subTest(day=day):
                head,rows=industry_table(day)
                self.assertEqual(len(rows),10)
                self.assertEqual(len(set(row[0] for row in rows)),10)
                self.assertIn("行业",head)
                for row in rows:
                    self.assertGreaterEqual(len(row),6)
                    self.assertTrue(row[0])
                    self.assertAlmostEqual(number(row[2])-number(row[1]),number(row[3]),places=2)

    def test_oct23_two_day_provenance_and_no_lookahead_claim(self):
        report=(ROOT/"reports/2026-10-23.md").read_text(encoding="utf-8")
        header,rows=industry_table("2026-10-23")
        self.assertIn("10月22日",header)
        self.assertIn("10月23日",header)
        self.assertIn("report_type: historical_reconstruction",report)
        self.assertIn("reconstructed_at: 2026-10-26",report)
        self.assertIn("202610223904241516",report)
        self.assertIn("202610233906344471",report)
        nums={r[0]:r for r in rows}
        self.assertAlmostEqual(number(nums["电子"][1]),-137.02)
        self.assertAlmostEqual(number(nums["电子"][2]),73.46)
        self.assertAlmostEqual(number(nums["计算机"][1]),-36.0)
        self.assertAlmostEqual(number(nums["计算机"][2]),37.11)
        self.assertIn("行业总成交金额",report)
        self.assertIn("不能伪造",report)

    def test_template_is_shared_and_non_destructive(self):
        html=(ROOT/"index.html").read_text(encoding="utf-8")
        template=(ROOT/"assets/report-template.js").read_text(encoding="utf-8")
        daily=(ROOT/"assets/daily.js").read_text(encoding="utf-8")
        source=(ROOT/"templates/daily-report-v1.md").read_text(encoding="utf-8")
        self.assertIn("assets/report-template.js",html)
        self.assertIn("template-overview",html)
        self.assertIn("RadarReportTemplate?.render?.",daily)
        self.assertIn("renderMarkdown(text)",daily)
        self.assertEqual(len(re.findall(r'key:"(?:selection|market|industry|funds|plan|review|risk|next|sources)"',template)),9)
        self.assertIn("industryGraphic",template)
        self.assertIn("原报告未单独覆盖",template)
        self.assertIn("10个申万一级行业双日对照",source)

if __name__=="__main__":
    unittest.main()
