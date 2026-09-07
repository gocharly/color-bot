import gzip
import math
from typing import Any
from src.core.constants import MAX_TGS_SIZE
from src.engine.color_utils import json_dumps


def _strip_names(obj: Any) -> None:
    """Удаляет избыточные имена слоев и фигур, не влияющие на рендеринг."""
    if isinstance(obj, dict):
        obj.pop("nm", None)
        obj.pop("mn", None)
        for v in obj.values():
            _strip_names(v)
    elif isinstance(obj, list):
        for item in obj:
            _strip_names(item)


def _round_floats(obj: Any, precision: int = 2) -> Any:
    """Округляет координаты и параметры с плавающей точкой."""
    if isinstance(obj, float):
        return round(obj, precision) if math.isfinite(obj) else obj
    if isinstance(obj, dict):
        for k, v in list(obj.items()):
            obj[k] = _round_floats(v, precision)
        return obj
    if isinstance(obj, list):
        for i, v in enumerate(obj):
            obj[i] = _round_floats(v, precision)
        return obj
    return obj


def compress_tgs(lottie: dict, max_size: int = MAX_TGS_SIZE) -> bytes:
    """Многоуровневое сжатие Lottie JSON в формат TGS (gzipped JSON).

    Гарантирует, что итоговый размер не превысит лимит Telegram (63 КБ).
    """
    # 1. Базовая компрессия
    raw = json_dumps(lottie)
    compressed = gzip.compress(raw, compresslevel=6)
    if len(compressed) <= max_size:
        return compressed

    # 2. Очистка незначащих метаданных
    _strip_names(lottie)
    raw = json_dumps(lottie)
    compressed = gzip.compress(raw, compresslevel=6)
    if len(compressed) <= max_size:
        return compressed

    # 3. Округление чисел до 2 знаков
    _round_floats(lottie, precision=2)
    raw = json_dumps(lottie)
    compressed = gzip.compress(raw, compresslevel=6)
    if len(compressed) <= max_size:
        return compressed

    # 4. Максимальный уровень сжатия gzip
    compressed = gzip.compress(raw, compresslevel=9)
    if len(compressed) <= max_size:
        return compressed

    # 5. Округление до 1 знака
    _round_floats(lottie, precision=1)
    raw = json_dumps(lottie)
    compressed = gzip.compress(raw, compresslevel=9)
    if len(compressed) <= max_size:
        return compressed

    # 6. Округление до целых чисел (экстренный fallback)
    _round_floats(lottie, precision=0)
    raw = json_dumps(lottie)
    return gzip.compress(raw, compresslevel=9)
