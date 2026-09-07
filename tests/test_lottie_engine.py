import copy
import unittest
from src.engine.color_utils import hex_to_rgb
from src.engine.lottie_engine import get_dominant_color, tint_lottie


class TestLottieEngine(unittest.TestCase):
    def setUp(self):
        self.sample_lottie = {
            "v": "5.5.2",
            "fr": 60,
            "ip": 0,
            "op": 180,
            "w": 512,
            "h": 512,
            "layers": [
                {
                    "ty": 4,
                    "nm": "Layer 1",
                    "shapes": [
                        {
                            "ty": "fl",
                            "nm": "Body Fill",
                            "c": {"a": 0, "k": [0.1, 0.1, 0.1, 1.0]},
                        },
                        {
                            "ty": "st",
                            "nm": "Outline Stroke",
                            "c": {"a": 0, "k": [1.0, 1.0, 1.0, 1.0]},
                        },
                    ],
                }
            ],
        }

    def test_single_color_recolor(self):
        lottie = copy.deepcopy(self.sample_lottie)
        tinted = tint_lottie(lottie, "#FF0000")

        # Проверяем заливку тела
        fl = tinted["layers"][0]["shapes"][0]
        self.assertAlmostEqual(fl["c"]["k"][0], 1.0, places=2)  # R
        self.assertAlmostEqual(fl["c"]["k"][1], 0.0, places=2)  # G
        self.assertAlmostEqual(fl["c"]["k"][2], 0.0, places=2)  # B

        # Проверяем обводку
        st = tinted["layers"][0]["shapes"][1]
        self.assertAlmostEqual(st["c"]["k"][0], 1.0, places=2)  # R
        self.assertAlmostEqual(st["c"]["k"][1], 0.0, places=2)  # G
        self.assertAlmostEqual(st["c"]["k"][2], 0.0, places=2)  # B

    def test_multi_zone_recolor(self):
        lottie = copy.deepcopy(self.sample_lottie)
        # Обводка: синий (#0000FF), Тело: зеленый (#00FF00)
        tinted = tint_lottie(lottie, ["#0000FF", "#00FF00"])

        fl = tinted["layers"][0]["shapes"][0]
        self.assertAlmostEqual(fl["c"]["k"][1], 1.0, places=2)  # Body is Green

        st = tinted["layers"][0]["shapes"][1]
        self.assertAlmostEqual(st["c"]["k"][2], 1.0, places=2)  # Stroke is Blue

    def test_animated_keyframes_ae2022(self):
        # Lottie с keyframes без поля 'e'
        lottie = {
            "v": "5.7.0",
            "layers": [
                {
                    "ty": 4,
                    "shapes": [
                        {
                            "ty": "fl",
                            "c": {
                                "a": 1,
                                "k": [
                                    {"t": 0, "s": [0.0, 0.0, 0.0, 1.0]},
                                    {"t": 30, "s": [0.5, 0.5, 0.5, 1.0]},
                                ],
                            },
                        }
                    ],
                }
            ],
        }
        tinted = tint_lottie(lottie, "#FF0000")
        kfs = tinted["layers"][0]["shapes"][0]["c"]["k"]
        # Начальный keyframe должен быть перекрашен
        self.assertAlmostEqual(kfs[0]["s"][0], 1.0, places=2)
        self.assertAlmostEqual(kfs[0]["s"][1], 0.0, places=2)

    def test_dominant_color(self):
        dom = get_dominant_color(self.sample_lottie)
        self.assertIsNotNone(dom)


if __name__ == "__main__":
    unittest.main()
