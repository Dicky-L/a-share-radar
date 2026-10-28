import tempfile
import unittest
from pathlib import Path
from scripts.check_daily_publication import verify

HEADINGS = [
    "一、本期选股结论",
    "二、全市场资金总览",
    "三、10个申万一级行业双日对照",
    "四、资金关注度与产业解读",
    "五、本期选股观察与卖出计划",
    "六、前期推荐与失败复盘",
    "七、仓位与卖出风险管理",
    "八、下一交易日验证清单",
    "九、数据口径、来源与局限",
]
SECTORS = ["电子", "通信", "计算机", "传媒", "汽车", "机械设备",
           "国防军工", "电力设备", "银行", "公用事业"]

def report(sectors=SECTORS, omit=None, status="original", backwards=False):
    pre = ("---\ndate: 2026-10-27\n"
           "title: A股启动与卖出雷达\nstatus: " + status +
           "\nsource: scheduled task\npreview: 截面完整核验\n---\n")
    heads = [h for h in HEADINGS if h != omit]
    if backwards:
        heads[0], heads[1] = heads[1], heads[0]
    parts = []
    for h in heads:
        parts.append("## " + h + "\n")
        if "10个申万" in h:
            parts.append("| 申万一级行业 | 前日主力净额 | 当日主力净额 | 变化 | 涨跌 | 判断 |\n"
                         "|---|---:|---:|---:|---:|---|\n")
            parts.extend(f"| {name} | +1.0 | +1.5 | +0.5 | +0.2% | 净流入 |\n" for name in sectors)
        parts.append(("股票市场说明与条件性判断；" * 12) + "\n")
    parts.append("来源：https://example.org/data （此地址仅为单元测试夹具）\n")
    return pre + "\n".join(parts)

class TestV1Publication(unittest.TestCase):
    def check(self, text):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "2026-10-27.md").write_text(text, encoding="utf-8")
            return verify("2026-10-27", Path(d))

    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(verify("2026-10-27", Path(d))[0])

    def test_valid_full_report(self):
        ok, message = self.check(report())
        self.assertTrue(ok, message)

    def test_missing_section(self):
        self.assertFalse(self.check(report(omit=HEADINGS[5]))[0])

    def test_wrong_section_order(self):
        self.assertFalse(self.check(report(backwards=True))[0])

    def test_only_nine_sectors(self):
        self.assertFalse(self.check(report(sectors=SECTORS[:-1]))[0])

    def test_duplicate_sector(self):
        self.assertFalse(self.check(report(sectors=SECTORS[:-1] + ["电子"]))[0])

    def test_summary_cannot_pass(self):
        self.assertFalse(self.check(report(status="summary"))[0])

    def test_reconstructed_cannot_pass(self):
        self.assertFalse(self.check(report().replace(
            "status: original", "status: original\nreport_type: historical_reconstruction"))[0])

if __name__ == "__main__":
    unittest.main()
