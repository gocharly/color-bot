import unittest
from src.engine.color_utils import (
    hex_to_rgb,
    rgb_to_hex,
    norm_rgb,
    parse_hex_list,
    resolve_zones,
    calc_luminance,
)


class TestColorUtils(unittest.TestCase):
    def test_hex_to_rgb(self):
        self.assertEqual(hex_to_rgb("#FF0000"), (255, 0, 0))
        self.assertEqual(hex_to_rgb("#00FF00"), (0, 255, 0))
        self.assertEqual(hex_to_rgb("#0000FF"), (0, 0, 255))
        self.assertEqual(hex_to_rgb("#FFFFFF"), (255, 255, 255))
        self.assertEqual(hex_to_rgb("#000000"), (0, 0, 0))

    def test_rgb_to_hex(self):
        self.assertEqual(rgb_to_hex(255, 0, 0), "#FF0000")
        self.assertEqual(rgb_to_hex(0, 122, 255), "#007AFF")

    def test_norm_rgb(self):
        self.assertEqual(norm_rgb("#FFFFFF"), (1.0, 1.0, 1.0))
        self.assertEqual(norm_rgb("#000000"), (0.0, 0.0, 0.0))
        self.assertIsNone(norm_rgb(None))

    def test_parse_hex_list(self):
        text = "#FF3B30, 007AFF #34C759 invalid_color #1C1C1E"
        parsed = parse_hex_list(text)
        self.assertEqual(parsed, ["#FF3B30", "#007AFF", "#34C759"])

    def test_resolve_zones_single_color(self):
        zones = resolve_zones("#FF3B30")
        expected = norm_rgb("#FF3B30")
        self.assertEqual(zones["stroke"], expected)
        self.assertEqual(zones["body"], expected)
        self.assertEqual(zones["text"], expected)

    def test_resolve_zones_multi(self):
        zones = resolve_zones(["#007AFF", "#1C1C1E", "#F2F2F7"])
        self.assertEqual(zones["stroke"], norm_rgb("#007AFF"))
        self.assertEqual(zones["body"], norm_rgb("#1C1C1E"))
        self.assertEqual(zones["text"], norm_rgb("#F2F2F7"))

    def test_calc_luminance(self):
        self.assertAlmostEqual(calc_luminance(1.0, 1.0, 1.0), 1.0)
        self.assertAlmostEqual(calc_luminance(0.0, 0.0, 0.0), 0.0)


if __name__ == "__main__":
    unittest.main()
