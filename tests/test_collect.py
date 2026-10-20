import pathlib
import tempfile
import unittest
from unittest.mock import Mock
from collect import normal_code, parse_quote, fetch_quotes, save_snapshot

DAY = "2026-10-20"

def quote(code="600000", stamp="20261020150001", price="9.23", amount="120000"):
    f = [""] * 54
    f[1], f[2], f[3], f[30], f[32], f[37] = "浦发银行", code, price, stamp, "1.5", amount
    return "v_sh" + code + '="' + "~".join(f) + '";'

class TestCollector(unittest.TestCase):
    def test_code(self):
        self.assertEqual(normal_code("sh600000"), "600000")
        self.assertEqual(normal_code("SZ300001"), "300001")
        self.assertIsNone(normal_code("bj830001"))
    def test_tencent_amount_in_wan(self):
        item = parse_quote(quote(), DAY)
        self.assertEqual(item["turnover_yi"], 12.0)
        self.assertEqual(item["price"], 9.23)
    def test_outdated_quote_refused(self):
        with self.assertRaises(ValueError):
            parse_quote(quote(stamp="20261019150000"), DAY)
    def test_incomplete_day_quote_refused(self):
        with self.assertRaises(ValueError):
            parse_quote(quote(stamp="20261020100000"), DAY)
    def test_missing_universe_is_error(self):
        response = Mock(content=quote().encode("gbk"))
        response.raise_for_status.return_value = None
        with self.assertRaises(RuntimeError):
            fetch_quotes(["600000", "600001", "600002"], DAY,
                         request_get=lambda *args, **kwargs: response)
    def test_incomplete_not_published(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                save_snapshot({"date":DAY, "market":{"turnover_yi":1}, "stocks":[]},
                              pathlib.Path(tmp))
            self.assertFalse((pathlib.Path(tmp) / "index.json").exists())

if __name__ == "__main__":
    unittest.main()
