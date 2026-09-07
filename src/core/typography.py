from typing import Dict, Optional


def make_card(title: str, params: Optional[Dict[str, str]] = None, footer: Optional[str] = None) -> str:
    """Форматирует карточку в соответствии со стандартами Taste Typography и Zero-Emoji.

    Оборачивает содержимое в <blockquote>, структурирует заголовок и параметры
    без принудительного капса — с мягкой и понятной типографикой.
    """
    lines = [f"<b>{title}</b>"]
    if params:
        lines.append("")
        for key, value in params.items():
            lines.append(f"• {key}: <code>{value}</code>")
    if footer:
        lines.append("")
        lines.append(footer)

    body = "\n".join(lines)
    return f"<blockquote>\n{body}\n</blockquote>"


def make_status_card(title: str, message: str, is_error: bool = False) -> str:
    """Генерирует аккуратную карточку статуса или подсказки."""
    header = f"<b>{title}</b>"
    if is_error:
        header = f"<b>Обратите внимание: {title}</b>"
    return f"<blockquote>\n{header}\n\n{message}\n</blockquote>"
