import glob
import io
import math
import os
import threading
import urllib.request
from typing import Any, List, Optional, Tuple
from src.core.logger import logger

try:
    from fontTools.pens.recordingPen import DecomposingRecordingPen
    from fontTools.ttLib import TTFont

    HAS_FONTTOOLS = True
except ImportError:
    HAS_FONTTOOLS = False

_FONT_BYTES_CACHE = {}
_THREAD_LOCAL = threading.local()

SYSTEM_FONT_SEARCH = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
    "/usr/share/fonts/truetype/comfortaa/Comfortaa-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/roboto/Roboto-Bold.ttf",
]

DEFAULT_CDN_FONT = "https://raw.githubusercontent.com/googlefonts/comfortaa/master/fonts/TTF/Comfortaa-Bold.ttf"


def ensure_font(custom_path: Optional[str] = None) -> Optional[str]:
    """Возвращает доступный путь к TTF шрифту."""
    if custom_path and os.path.exists(custom_path):
        return custom_path

    # Проверка кеша в assets/fonts
    local_font = "assets/fonts/Comfortaa-Bold.ttf"
    if os.path.exists(local_font) and os.path.getsize(local_font) > 10000:
        return local_font

    # Системные шрифты
    for p in SYSTEM_FONT_SEARCH:
        if os.path.exists(p):
            return p

    # Поиск любых .ttf шрифтов в системе
    for p in glob.glob("/System/Library/Fonts/**/*.ttf", recursive=True):
        return p

    # Попытка скачать Comfortaa
    os.makedirs("assets/fonts", exist_ok=True)
    try:
        logger.info("Скачивание эталонного шрифта Comfortaa-Bold...")
        urllib.request.urlretrieve(DEFAULT_CDN_FONT, local_font)
        if os.path.exists(local_font) and os.path.getsize(local_font) > 10000:
            return local_font
    except Exception as e:
        logger.warning(f"Не удалось скачать шрифт Comfortaa: {e}")

    return None


def get_cached_ttfont(font_path: str):
    """Потокобезопасное получение экземпляра TTFont."""
    data = _FONT_BYTES_CACHE.get(font_path)
    if data is None:
        with open(font_path, "rb") as f:
            data = f.read()
        _FONT_BYTES_CACHE[font_path] = data

    if not hasattr(_THREAD_LOCAL, "fonts"):
        _THREAD_LOCAL.fonts = {}

    key = (font_path, len(data))
    if key not in _THREAD_LOCAL.fonts:
        _THREAD_LOCAL.fonts[key] = TTFont(io.BytesIO(data))
    return _THREAD_LOCAL.fonts[key]


def text_to_lottie_shapes(
    text: str,
    font_path: str,
    cx: float,
    cy: float,
    height: float,
    max_width: Optional[float] = None,
) -> List[dict]:
    """Векторизует строку текста в список кривых Безье (sh) для Lottie."""
    if not HAS_FONTTOOLS:
        logger.error("fontTools не установлен")
        return []

    try:
        ft = get_cached_ttfont(font_path)
        gs = ft.getGlyphSet()
        cm = ft.getBestCmap() or {}
    except Exception as e:
        logger.error(f"Ошибка загрузки шрифта {font_path}: {e}")
        return []

    upm = ft["head"].unitsPerEm
    os2 = ft.get("OS/2")
    cap_h = float(getattr(os2, "sCapHeight", 0) or getattr(os2, "sTypoAscender", upm * 0.72))
    if cap_h <= 0:
        cap_h = upm * 0.72

    scale = height / cap_h
    total_adv = 0.0
    glyph_list = []

    for ch in text:
        gn = cm.get(ord(ch))
        if not gn or gn not in gs:
            fb = {ord("'"): [0x2019, 0x02BC], ord("–"): [0x002D], ord("—"): [0x002D]}
            for alt in fb.get(ord(ch), []):
                gn = cm.get(alt)
                if gn and gn in gs:
                    break
            else:
                gn = None
        adv = float(gs[gn].width) if gn and gn in gs else upm * 0.35
        glyph_list.append((gn, adv))
        total_adv += adv

    if max_width and total_adv > 0:
        scale = min(scale, (max_width / (total_adv * scale) * scale) * 0.92)

    start_x = cx - total_adv * scale / 2.0
    base_y = cy + (cap_h / 2.0) * scale
    shapes: List[dict] = []
    cur_x = start_x

    for gn, adv in glyph_list:
        if gn is None:
            cur_x += adv * scale
            continue
        try:
            pen = DecomposingRecordingPen(gs)
            gs[gn].draw(pen)
            vs_, ii_, oo_ = [], [], []

            def _close():
                if vs_:
                    shapes.append(
                        {
                            "ty": "sh",
                            "nm": "p",
                            "ks": {
                                "a": 0,
                                "k": {
                                    "c": True,
                                    "v": [list(v) for v in vs_],
                                    "i": [list(v) for v in ii_],
                                    "o": [list(v) for v in oo_],
                                },
                            },
                        }
                    )

            for op, args in pen.value:
                if op == "moveTo":
                    _close()
                    vs_.clear()
                    ii_.clear()
                    oo_.clear()
                    fx, fy = args[0]
                    lx = fx * scale + cur_x
                    ly = base_y - fy * scale
                    vs_.append([lx, ly])
                    ii_.append([0.0, 0.0])
                    oo_.append([0.0, 0.0])
                elif op == "lineTo":
                    fx, fy = args[0]
                    lx = fx * scale + cur_x
                    ly = base_y - fy * scale
                    vs_.append([lx, ly])
                    ii_.append([0.0, 0.0])
                    oo_.append([0.0, 0.0])
                elif op == "curveTo":
                    (c1x, c1y), (c2x, c2y), (ex, ey) = args
                    pvx, pvy = vs_[-1]
                    oo_[-1] = [c1x * scale + cur_x - pvx, base_y - c1y * scale - pvy]
                    nvx = ex * scale + cur_x
                    nvy = base_y - ey * scale
                    vs_.append([nvx, nvy])
                    ii_.append([c2x * scale + cur_x - nvx, base_y - c2y * scale - nvy])
                    oo_.append([0.0, 0.0])
                elif op == "qCurveTo":
                    pts = list(args)
                    p0x, p0y = vs_[-1]
                    for qi in range(len(pts) - 1):
                        qcx, qcy = pts[qi]
                        qex, qey = (
                            pts[qi + 1]
                            if qi == len(pts) - 2
                            else (
                                (pts[qi][0] + pts[qi + 1][0]) / 2,
                                (pts[qi][1] + pts[qi + 1][1]) / 2,
                            )
                        )
                        c1s = (p0x + 2 / 3 * (qcx * scale + cur_x - p0x), p0y + 2 / 3 * (base_y - qcy * scale - p0y))
                        c2s = (qex * scale + cur_x + 2 / 3 * (qcx * scale + cur_x - (qex * scale + cur_x)), base_y - qey * scale + 2 / 3 * (base_y - qcy * scale - (base_y - qey * scale)))
                        oo_[-1] = [c1s[0] - p0x, c1s[1] - p0y]
                        vs_.append(list((qex * scale + cur_x, base_y - qey * scale)))
                        ii_.append([c2s[0] - (qex * scale + cur_x), c2s[1] - (base_y - qey * scale)])
                        oo_.append([0.0, 0.0])
                        p0x, p0y = qex * scale + cur_x, base_y - qey * scale
                elif op in ("endPath", "closePath"):
                    _close()
                    vs_.clear()
                    ii_.clear()
                    oo_.clear()
            _close()
        except Exception as e:
            logger.warning(f"Ошибка отрисовки глифа {gn}: {e}")
        cur_x += adv * scale

    return shapes


def _collect_path_verts(obj: Any) -> List[Tuple[float, float]]:
    verts: List[Tuple[float, float]] = []

    def walk(o: Any):
        if isinstance(o, dict):
            if o.get("ty") == "sh":
                k = o.get("ks", {}).get("k", {})
                if isinstance(k, dict) and "v" in k:
                    for v in k["v"]:
                        verts.append((float(v[0]), float(v[1])))
            for val in o.values():
                walk(val)
        elif isinstance(o, list):
            for item in o:
                walk(item)

    walk(obj)
    return verts


def _get_textgroup_bounds(lottie: dict) -> Optional[Tuple[float, float, float, float]]:
    """Находит координаты текстовой области в Lottie."""
    keywords = {"textgroup", "text", "letters", "emoji", "text shape", "logo", "label", "caption"}
    elements = []
    todo = list(lottie.get("layers", []))
    for a in lottie.get("assets", []):
        todo.extend(a.get("layers", []))

    while todo:
        el = todo.pop()
        elements.append(el)
        if "shapes" in el:
            todo.extend(el["shapes"])
        if "it" in el:
            todo.extend(el["it"])

    # 1. Слой типа 5 (Text Layer)
    for el in elements:
        if el.get("ty") == 5:
            pos = el.get("ks", {}).get("p", {}).get("k", [256, 256])
            if isinstance(pos, list) and len(pos) >= 2 and isinstance(pos[0], (int, float)):
                cx, cy = float(pos[0]), float(pos[1])
                return (cx - 200.0, cy - 30.0, cx + 200.0, cy + 30.0)

    # 2. Группы с ключевыми словами
    for el in elements:
        nm = (el.get("nm") or "").lower()
        if any(kw in nm for kw in keywords) and "user" not in nm:
            verts = _collect_path_verts(el)
            if verts:
                xs = [v[0] for v in verts]
                ys = [v[1] for v in verts]
                return (min(xs), min(ys), max(xs), max(ys))

    return None


def modify_lottie_text(lottie: dict, new_text: str, font_path: Optional[str] = None, scale_factor: float = 1.0) -> bool:
    """Заменяет текст в анимированном Lottie стикере."""
    if not font_path:
        font_path = ensure_font()
    if not font_path:
        return False

    bounds = _get_textgroup_bounds(lottie)
    if not bounds:
        # Добавляем стандартный текстовый слой, если его не было
        bounds = (100.0, 380.0, 412.0, 460.0)

    x1, y1, x2, y2 = bounds
    cx = (x1 + x2) / 2.0
    cy = (y1 + y2) / 2.0
    h = max(abs(y2 - y1), 10.0) * scale_factor
    w = max(abs(x2 - x1), 10.0) * scale_factor * 1.5

    shapes = text_to_lottie_shapes(new_text, font_path, cx, cy, h, max_width=w)
    if not shapes:
        return False

    # Внедрение в слои
    patched = False

    def walk_patch(obj: Any):
        nonlocal patched
        if isinstance(obj, dict):
            nm = (obj.get("nm") or "").lower()
            if obj.get("ty") == "gr" and any(k in nm for k in ("text", "caption", "label")):
                items = obj.get("it", [])
                style = [x for x in items if x.get("ty") not in ("sh", "el", "rc", "sr")]
                obj["it"] = shapes + style
                patched = True
                return
            for v in obj.values():
                walk_patch(v)
        elif isinstance(obj, list):
            for item in obj:
                walk_patch(item)

    walk_patch(lottie)

    if not patched:
        # Добавляем новый Shape Layer наверх
        new_layer = {
            "ty": 4,
            "nm": "Text Layer",
            "sr": 1,
            "st": 0,
            "op": 9999,
            "ip": 0,
            "ind": 1,
            "ks": {
                "a": {"a": 0, "k": [0, 0, 0]},
                "p": {"a": 0, "k": [0, 0, 0]},
                "s": {"a": 0, "k": [100, 100, 100]},
                "r": {"a": 0, "k": 0},
                "o": {"a": 0, "k": 100},
            },
            "shapes": shapes
            + [
                {
                    "ty": "fl",
                    "c": {"a": 0, "k": [1, 1, 1, 1]},
                    "o": {"a": 0, "k": 100},
                    "nm": "Fill 1",
                }
            ],
        }
        lottie.setdefault("layers", []).insert(0, new_layer)
        patched = True

    return patched
