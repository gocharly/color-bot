import io
import unittest
from PIL import Image
from src.engine.webp_engine import tint_image


class TestWebpEngine(unittest.TestCase):
    def setUp(self):
        # Создаем тестовое RGBA изображение
        img = Image.new("RGBA", (256, 256), color=(128, 128, 128, 255))
        buf = io.BytesIO()
        img.save(buf, format="WEBP")
        self.sample_bytes = buf.getvalue()

    def test_tint_webp(self):
        tinted_bytes = tint_image(self.sample_bytes, "#007AFF")
        self.assertGreater(len(tinted_bytes), 0)

        # Проверяем, что результат валидный WebP
        result_img = Image.open(io.BytesIO(tinted_bytes))
        self.assertEqual(result_img.format, "WEBP")
        self.assertEqual(result_img.size, (512, 512))  # Автоматический ресайз под стандартный размер стикера

    def test_tint_custom_emoji(self):
        tinted_bytes = tint_image(self.sample_bytes, "#FF3B30", is_emoji=True)
        result_img = Image.open(io.BytesIO(tinted_bytes))
        self.assertEqual(result_img.size, (100, 100))  # Размер кастомного эмодзи Telegram


if __name__ == "__main__":
    unittest.main()
