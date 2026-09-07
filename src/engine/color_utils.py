import json
import re
from typing import Any, Dict, List, Optional, Tuple

try:
    import orjson

    HAS_ORJSON = True
except ImportError:
    HAS_ORJSON = False


def json_loads(data: bytes | str) -> dict:
    """Быстрый парсинг JSON через orjson при наличии, либо json."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    if HAS_ORJSON:
        return orjson.loads(data)
    return json.loads(data.decode("utf-8"))


def json_dumps(obj: Any, indent: bool = False) -> bytes:
    """Быстрая сериализация JSON."""
    if HAS_ORJSON:
        if indent:
            return orjson.dumps(obj, option=orjson.OPT_INDENT_2)
        return orjson.dumps(obj)
    if indent:
        return json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")
    return json.dumps(obj, separators=(",", ":")).encode("utf-8")


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Преобразует HEX (#RRGGBB) в кортеж (r, g, b) от 0 до 255."""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Преобразует RGB (0..255) в HEX строку вида #RRGGBB."""
    return f"#{r:02X}{g:02X}{b:02X}"


def norm_rgb(hex_color: Optional[str]) -> Optional[Tuple[float, float, float]]:
    """Преобразует HEX в нормализованные (r, g, b) в диапазоне 0.0..1.0."""
    if not hex_color:
        return None
    r, g, b = hex_to_rgb(hex_color)
    return (r / 255.0, g / 255.0, b / 255.0)


def calc_luminance(r: float, g: float, b: float) -> float:
    """Вычисляет перцептивную яркость по стандарту Rec. 601."""
    return 0.299 * r + 0.587 * g + 0.114 * b


def zones_from_list(hex_list: List[str]) -> Dict[str, Optional[str]]:
    """Формирует карту зон из списка 1..3 HEX цветов.

    1 цвет  -> все зоны
    2 цвета -> обводка (1-й), тело+лого (2-й)
    3 цвета -> обводка (1-й), тело (2-й), лого/текст (3-й)
    """
    valid = [c.upper() for c in hex_list if c]
    if not valid:
        return {"stroke": None, "body": None, "text": None}
    c0 = valid[0]
    body = valid[1] if len(valid) >= 2 else c0
    text = valid[2] if len(valid) >= 3 else body
    return {"stroke": c0, "body": body, "text": text}


def resolve_zones(colors: Any) -> Dict[str, Optional[Tuple[float, float, float]]]:
    """Приводит различные форматы ввода к словарю зон с нормализованными цветами 0..1.

    Возвращает dict с ключами: 'stroke', 'body', 'text'.
    """
    if isinstance(colors, str):
        c = norm_rgb(colors)
        return {"stroke": c, "body": c, "text": c}

    if isinstance(colors, (list, tuple)):
        z = zones_from_list(list(colors))
        return {
            "stroke": norm_rgb(z.get("stroke")),
            "body": norm_rgb(z.get("body")),
            "text": norm_rgb(z.get("text")),
        }

    if isinstance(colors, dict):
        return {
            "stroke": norm_rgb(colors.get("stroke")),
            "body": norm_rgb(colors.get("body")),
            "text": norm_rgb(colors.get("text")),
        }

    return {"stroke": None, "body": None, "text": None}


def parse_hex_list(text: str) -> List[str]:
    """Извлекает из текста до 3 корректных HEX кодов."""
    out: List[str] = []
    tokens = re.split(r"[\s,]+", (text or "").strip())
    for tok in tokens:
        if not tok:
            continue
        h = tok if tok.startswith("#") else f"#{tok}"
        if re.fullmatch(r"#[0-9a-fA-F]{6}", h):
            h_upper = f"#{h[1:].upper()}"
            if h_upper not in out:
                out.append(h_upper)
    return out[:3]
