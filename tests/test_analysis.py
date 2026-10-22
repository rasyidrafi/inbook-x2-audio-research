import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("analysis", Path(__file__).resolve().parents[1]
                                             / "scripts/analyze-driver.py")
assert spec is not None and spec.loader is not None
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)


class EvidenceParsing(unittest.TestCase):
    def test_board_section_does_not_leak_generic_defaults(self):
        text = "[generic]\nHKR,ESAuDsetting,Mode,0x10001,1\n[board]\nHKR,ESAuDsetting,Mode,0x10001,0 ; steady\n[other]\nHKR,ESAuDsetting,Mode,0x10001,3\n"
        self.assertEqual(analysis.inf_settings(text, "board"), {"Mode": 0})

    def test_balanced_casts_and_nested_calls(self):
        result = list(analysis.call_arguments("write((longlong)p, 0x14, choose(a, b));", "write"))
        self.assertEqual(result, [(1, ["(longlong)p", "0x14", "choose(a, b)"])])

    def test_dynamic_values_are_not_guessed(self):
        self.assertIsNone(analysis.literal("ctx[0x14]"))
        self.assertIsNone(analysis.literal("0x10 | value"))
        self.assertEqual(analysis.literal(r"'\x01'"), 1)
        self.assertEqual(analysis.literal(r"'\0'"), 0)

    def test_truncated_call_rejected(self):
        with self.assertRaises(ValueError):
            list(analysis.call_arguments("write(p, 1,", "write"))


if __name__ == "__main__":
    unittest.main()
