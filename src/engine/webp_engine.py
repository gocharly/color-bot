import io
from typing import Any
from PIL import Image, ImageChops
from src.engine.color_utils import resolve_zones


def tint_image(data: bytes, colors: Any, is_emoji: bool = False) -> bytes:
    """Тонирует растровое WebP изображение с сохранением альфа-канала.

    Цвет тела (body) используется в качестве основного целевого тона.
    """
    zones = resolve_zones(colors)
    target = zones["body"] or zones["stroke"] or zones["text"]

    target_size = 100 if is_emoji else 512

    img = Image.open(io.BytesIO(data)).convert("RGBA")
    if img.size != (target_size, target_size):
        img = img.resize((target_size, target_size), Image.Resampling.LANCZOS)

    if target is None:
        out = io.BytesIO()
        img.save(out, format="WEBP", lossless=True)
        return out.getvalue()

    r_target, g_target, b_target = int(target[0] * 255), int(target[1] * 255), int(target[2] * 255)
    r, g, b, alpha = img.split()

    # Извлечение относительной светлоты пикселей
    max_rg = ImageChops.lighter(r, g)
    val = ImageChops.lighter(max_rg, b)

    lut_r = [int(i * r_target / 255) for i in range(256)]
    lut_g = [int(i * g_target / 255) for i in range(256)]
    lut_b = [int(i * b_target / 255) for i in range(256)]

    rn = val.point(lut_r)
    gn = val.point(lut_g)
    bn = val.point(lut_b)

    tinted = Image.merge("RGBA", (rn, gn, bn, alpha))
    out = io.BytesIO()
    tinted.save(out, format="WEBP", lossless=True)
    return out.getvalue()
