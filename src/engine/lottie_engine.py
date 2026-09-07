from typing import Any, Callable, Dict, List, Optional, Tuple
from src.core.constants import LOGO_SPLIT_MIN_GAP, RECOLOR_DARK_THRESHOLD
from src.engine.color_utils import (
    calc_luminance,
    hex_to_rgb,
    rgb_to_hex,
    resolve_zones,
)


def _tinted(nr: float, ng: float, nb: float, gray: float) -> Tuple[float, float, float]:
    """Применяет целевой оттенок с учётом темного порога."""
    if gray < RECOLOR_DARK_THRESHOLD:
        return nr, ng, nb
    return nr * gray, ng * gray, nb * gray


def _recolor_rgb(val: List[Any], nr: float, ng: float, nb: float) -> List[Any]:
    """Перекрашивает список [r, g, b] или [r, g, b, a] с сохранением прозрачности."""
    if len(val) < 3 or not isinstance(val[0], (int, float)):
        return val
    gray = calc_luminance(val[0], val[1], val[2])
    alpha = val[3] if len(val) > 3 else 1.0
    r, g, b = _tinted(nr, ng, nb, gray)
    return [r, g, b, alpha]


def _recolor_gradient_stops(raw: List[Any], p: int, nr: float, ng: float, nb: float) -> List[Any]:
    """Перекрашивает стопы градиента Lottie (первые p*4 значений — цвет, далее альфа)."""
    color_len = p * 4
    if len(raw) < color_len:
        color_len = (len(raw) // 4) * 4

    new_raw = list(raw)
    i = 0
    while i + 3 < color_len:
        gray = calc_luminance(new_raw[i + 1], new_raw[i + 2], new_raw[i + 3])
        new_raw[i + 1], new_raw[i + 2], new_raw[i + 3] = _tinted(nr, ng, nb, gray)
        i += 4
    return new_raw


def _fl_luminance(prop: dict) -> Optional[float]:
    """Извлекает яркость заливки 'fl'."""
    if not isinstance(prop, dict):
        return None
    k = prop.get("k")
    col = None
    if isinstance(k, list) and len(k) >= 3 and isinstance(k[0], (int, float)):
        col = k
    elif isinstance(k, list):
        for kf in k:
            if isinstance(kf, dict):
                s = kf.get("s")
                if isinstance(s, list) and len(s) >= 3 and isinstance(s[0], (int, float)):
                    col = s
                    break
    if not col:
        return None
    return calc_luminance(col[0], col[1], col[2])


def _decide_logo_split(lums: List[float]) -> Optional[Callable[[float], bool]]:
    """Определяет границу разделения между телом и логотипом по спектру яркостей."""
    vals = sorted(set(round(l, 4) for l in lums))
    if len(vals) < 2:
        return None
    gap, idx = max((vals[i + 1] - vals[i], i) for i in range(len(vals) - 1))
    if gap < LOGO_SPLIT_MIN_GAP:
        return None
    threshold = (vals[idx] + vals[idx + 1]) / 2.0
    return lambda lum: lum >= threshold


def tint_lottie(lottie_json: dict, colors: Any) -> dict:
    """Перекрашивает Lottie JSON AST по зонам (обводка, тело, логотип/текст).

    Поддерживает:
      - Shape fill (fl) и gradient fill (gf) -> тело
      - Shape stroke (st) и gradient stroke (gs) -> обводка
      - Text layers (t) и яркие элементы лого -> текст
      - Keyframes без поля 'e' (After Effects 2022+ формат Telegram)
    """
    zones = resolve_zones(colors)
    z_stroke = zones["stroke"]
    z_body = zones["body"]
    z_text = zones["text"]

    # Автодетект логотипа по яркости, если задан отдельный цвет текста
    is_logo: Optional[Callable[[float], bool]] = None
    if z_text is not None and z_text != z_body:
        fl_lums: List[float] = []

        def _scan_fl(o: Any) -> None:
            if isinstance(o, dict):
                if o.get("ty") == "fl":
                    lu = _fl_luminance(o.get("c", {}))
                    if lu is not None:
                        fl_lums.append(lu)
                for v in o.values():
                    _scan_fl(v)
            elif isinstance(o, list):
                for item in o:
                    _scan_fl(item)

        _scan_fl(lottie_json)
        is_logo = _decide_logo_split(fl_lums)

    def _recolor_prop(prop: dict, zc: Optional[Tuple[float, float, float]]) -> None:
        if zc is None or not isinstance(prop, dict):
            return
        nr, ng, nb = zc
        k = prop.get("k")
        if k is None:
            return

        if isinstance(k, list):
            if len(k) >= 3 and isinstance(k[0], (int, float)):
                prop["k"] = _recolor_rgb(k, nr, ng, nb)
            else:
                for kf in k:
                    if not isinstance(kf, dict):
                        continue
                    val_s = kf.get("s")
                    if isinstance(val_s, list) and len(val_s) >= 3 and isinstance(val_s[0], (int, float)):
                        kf["s"] = _recolor_rgb(val_s, nr, ng, nb)
                    val_e = kf.get("e")
                    if isinstance(val_e, list) and len(val_e) >= 3 and isinstance(val_e[0], (int, float)):
                        kf["e"] = _recolor_rgb(val_e, nr, ng, nb)

    def _recolor_grad_obj(g_obj: dict, zc: Optional[Tuple[float, float, float]]) -> None:
        if zc is None or not isinstance(g_obj, dict):
            return
        nr, ng, nb = zc
        p = int(g_obj.get("p", 0))
        if p == 0:
            return
        k_prop = g_obj.get("k")
        if not isinstance(k_prop, dict):
            return
        raw = k_prop.get("k")
        if raw is None:
            return

        if isinstance(raw, list) and raw and isinstance(raw[0], (int, float)):
            k_prop["k"] = _recolor_gradient_stops(raw, p, nr, ng, nb)
        elif isinstance(raw, list):
            for kf in raw:
                if not isinstance(kf, dict):
                    continue
                for field in ("s", "e"):
                    val = kf.get(field)
                    if isinstance(val, list) and val and isinstance(val[0], (int, float)):
                        kf[field] = _recolor_gradient_stops(val, p, nr, ng, nb)

    def _walk(obj: Any) -> None:
        if isinstance(obj, dict):
            ty = obj.get("ty", "")

            # Shape fill
            if ty == "fl":
                prop = obj.get("c", {})
                zc = z_body
                if is_logo is not None:
                    lu = _fl_luminance(prop)
                    if lu is not None and is_logo(lu):
                        zc = z_text
                _recolor_prop(prop, zc)
                return

            # Shape stroke
            if ty == "st":
                _recolor_prop(obj.get("c", {}), z_stroke)
                return

            # Gradient fill
            if ty == "gf":
                _recolor_grad_obj(obj.get("g", {}), z_body)
                return

            # Gradient stroke
            if ty == "gs":
                _recolor_grad_obj(obj.get("g", {}), z_stroke)
                return

            # Solid color layer
            sc_val = obj.get("sc")
            if z_body is not None and isinstance(sc_val, str) and sc_val.startswith("#"):
                nr, ng, nb = z_body
                try:
                    sr, sg, sb = hex_to_rgb(sc_val)
                    gray = calc_luminance(sr / 255.0, sg / 255.0, sb / 255.0)
                    tr, tg, tb = _tinted(nr, ng, nb, gray)
                    obj["sc"] = rgb_to_hex(int(tr * 255), int(tg * 255), int(tb * 255))
                except Exception:
                    pass

            # Text layer: t.d.k[i].s.fc / sc
            t_obj = obj.get("t")
            if z_text is not None and isinstance(t_obj, dict):
                nr, ng, nb = z_text
                d_obj = t_obj.get("d")
                if isinstance(d_obj, dict):
                    for kf in d_obj.get("k", []):
                        if isinstance(kf, dict):
                            s_obj = kf.get("s", {})
                            if isinstance(s_obj, dict):
                                for field in ("fc", "sc"):
                                    col = s_obj.get(field)
                                    if isinstance(col, list) and len(col) >= 3:
                                        gray = calc_luminance(col[0], col[1], col[2])
                                        alpha = col[3] if len(col) > 3 else 1.0
                                        tr, tg, tb = _tinted(nr, ng, nb, gray)
                                        s_obj[field] = [tr, tg, tb, alpha]

            for v in obj.values():
                _walk(v)

        elif isinstance(obj, list):
            for item in obj:
                _walk(item)

    _walk(lottie_json)
    return lottie_json


def get_dominant_color(lottie_json: dict) -> Optional[str]:
    """Определяет преобладающий цвет в Lottie (для автозаголовков)."""
    candidates: List[Tuple[int, str]] = []

    def _extract_static(c_prop: Any) -> Optional[str]:
        if not isinstance(c_prop, dict):
            return None
        k = c_prop.get("k", [])
        if isinstance(k, list) and len(k) >= 3 and isinstance(k[0], (int, float)):
            return rgb_to_hex(int(k[0] * 255), int(k[1] * 255), int(k[2] * 255))
        if isinstance(k, list):
            for kf in k:
                if isinstance(kf, dict):
                    s = kf.get("s")
                    if isinstance(s, list) and len(s) >= 3 and isinstance(s[0], (int, float)):
                        return rgb_to_hex(int(s[0] * 255), int(s[1] * 255), int(s[2] * 255))
        return None

    def _walk(obj: Any) -> None:
        if isinstance(obj, dict):
            ty = obj.get("ty", "")
            if ty == "fl":
                c = _extract_static(obj.get("c", {}))
                if c:
                    candidates.append((0, c))
            elif ty == "st":
                c = _extract_static(obj.get("c", {}))
                if c:
                    candidates.append((1, c))
            for v in obj.values():
                _walk(v)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)

    _walk(lottie_json)
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0])
    return candidates[0][1]
