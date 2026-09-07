import gzip
import unittest
from src.core.constants import MAX_TGS_SIZE
from src.engine.color_utils import json_loads
from src.engine.lottie_compress import compress_tgs


class TestCompress(unittest.TestCase):
    def test_compress_small(self):
        lottie = {
            "v": "5.5.2",
            "fr": 60,
            "ip": 0,
            "op": 60,
            "w": 512,
            "h": 512,
            "layers": [{"ty": 4, "nm": "TestLayer", "shapes": []}],
        }
        compressed = compress_tgs(lottie)
        self.assertLessEqual(len(compressed), MAX_TGS_SIZE)

        # Проверяем, что распаковывается обратно в корректный JSON
        decompressed = gzip.decompress(compressed)
        data = json_loads(decompressed)
        self.assertEqual(data["v"], "5.5.2")

    def test_compress_large_floats(self):
        # Большой массив с точными числами с плавающей точкой
        large_points = [[i * 1.23456789, i * 2.98765432] for i in range(500)]
        lottie = {
            "v": "5.5.2",
            "layers": [
                {
                    "ty": 4,
                    "nm": "HeavyLayer",
                    "shapes": [
                        {
                            "ty": "sh",
                            "ks": {
                                "k": {
                                    "v": large_points,
                                    "i": [[0.0, 0.0]] * 500,
                                    "o": [[0.0, 0.0]] * 500,
                                }
                            },
                        }
                    ],
                }
            ],
        }
        compressed = compress_tgs(lottie)
        self.assertLessEqual(len(compressed), MAX_TGS_SIZE)


if __name__ == "__main__":
    unittest.main()
