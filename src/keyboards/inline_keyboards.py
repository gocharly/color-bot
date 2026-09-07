from typing import Dict, List, Optional
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from src.core.constants import ZONE_LABELS
from src.keyboards.callbacks import ActionCallback, ColorCallback, PackActionCallback, ZoneCallback

# Цветовая палитра, логически сгруппированная 3-в-ряд по спектрам:
# 1. Тёплые оттенки
# 2. Природные и холодные
# 3. Акцентные и пастельные
# 4. Монохромные
COLOR_GROUPS = [
    [("Красный", "#FF3B30"), ("Оранжевый", "#FF9500"), ("Жёлтый", "#FFCC00")],
    [("Зелёный", "#34C759"), ("Голубой", "#5AC8FA"), ("Синий", "#007AFF")],
    [("Фиолетовый", "#AF52DE"), ("Розовый", "#FF2D55"), ("Коричневый", "#A2845E")],
    [("Чёрный", "#1C1C1E"), ("Серый", "#8E8E93"), ("Белый", "#F2F2F7")],
]


def get_color_palette_keyboard(
    active_zone: str = "body",
    recent_colors: Optional[List[str]] = None,
    is_animated: bool = True,
) -> InlineKeyboardMarkup:
    """Генерация стильной компактной палитры (3 цвета в ряд вместо длинного списка 2-в-ряд)."""
    builder = InlineKeyboardBuilder()

    # Недавние цвета в 1 аккуратный верхний ряд (до 3 цветов)
    if recent_colors:
        for c in recent_colors[:3]:
            builder.button(
                text=f"• {c}",
                callback_data=ColorCallback(hex=c, zone=active_zone),
            )
        builder.adjust(len(recent_colors[:3]))

    # Сетка палитры 3-в-ряд
    for row in COLOR_GROUPS:
        row_buttons = [
            InlineKeyboardButton(
                text=label,
                callback_data=ColorCallback(hex=hex_val, zone=active_zone).pack(),
            )
            for label, hex_val in row
        ]
        builder.row(*row_buttons)

    # Функциональные кнопки в два сбалансированных уровня
    builder.row(
        InlineKeyboardButton(
            text="Свой оттенок (HEX)",
            callback_data=ActionCallback(action="custom_hex").pack(),
        )
    )

    if is_animated:
        builder.row(
            InlineKeyboardButton(
                text="Раздельные зоны",
                callback_data=ActionCallback(action="zones_menu").pack(),
            ),
            InlineKeyboardButton(
                text="Замена текста",
                callback_data=ActionCallback(action="change_text").pack(),
            ),
        )

    return builder.as_markup()


def get_zones_keyboard(current_zones: Dict[str, Optional[str]], is_emoji: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура выбора зон с понятной двухуровневой группировкой."""
    builder = InlineKeyboardBuilder()

    # 1. Верхняя кнопка — всё целиком
    all_status = current_zones.get("all") or "исходный"
    builder.row(
        InlineKeyboardButton(
            text=f"Весь элемент целиком · {all_status}",
            callback_data=ZoneCallback(zone="all").pack(),
        )
    )

    # 2. Пара основных зон: Контур и Тело
    stroke_status = current_zones.get("stroke") or "исходный"
    body_status = current_zones.get("body") or "исходный"
    builder.row(
        InlineKeyboardButton(
            text=f"Контур: {stroke_status}",
            callback_data=ZoneCallback(zone="stroke").pack(),
        ),
        InlineKeyboardButton(
            text=f"Тело: {body_status}",
            callback_data=ZoneCallback(zone="body").pack(),
        ),
    )

    # 3. Детали и логотип
    text_status = current_zones.get("text") or "исходный"
    builder.row(
        InlineKeyboardButton(
            text=f"Детали и текст: {text_status}",
            callback_data=ZoneCallback(zone="text").pack(),
        )
    )

    # 4. Действия
    builder.row(
        InlineKeyboardButton(
            text="Готово, применить цвета",
            callback_data=ActionCallback(action="render_zones").pack(),
        ),
        InlineKeyboardButton(
            text="« К палитре",
            callback_data=ActionCallback(action="back_to_palette").pack(),
        ),
    )

    return builder.as_markup()


def get_result_keyboard(is_emoji: bool = False, has_pack: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура действий после создания перекрашенного стикера или эмодзи."""
    builder = InlineKeyboardBuilder()

    if is_emoji:
        builder.button(
            text="Создать эмодзи-пак (в клавиатуру)",
            callback_data=ActionCallback(action="add_pack"),
        )
        builder.button(
            text="Отправить в чат (как стикер)",
            callback_data=ActionCallback(action="instant_sticker"),
        )
        builder.adjust(1)
    else:
        builder.button(
            text="Отправить стикером в чат",
            callback_data=ActionCallback(action="instant_sticker"),
        )
        builder.button(
            text="Создать стикерпак",
            callback_data=ActionCallback(action="add_pack"),
        )
        builder.adjust(1)

    builder.button(
        text="Скачать исходный файл",
        callback_data=ActionCallback(action="send_file"),
    )
    builder.button(
        text="Попробовать другой цвет",
        callback_data=ActionCallback(action="back_to_palette"),
    )
    builder.adjust(2)

    return builder.as_markup()


def get_pack_creation_keyboard(is_emoji: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура вариантов создания стикерпака или эмодзи-пака."""
    builder = InlineKeyboardBuilder()

    pack_type = "эмодзи-пак" if is_emoji else "стикерпак"

    builder.button(
        text=f"Создать {pack_type} (в 1 клик)",
        callback_data=PackActionCallback(action="auto"),
    )
    builder.button(
        text="Придумать своё название и ссылку",
        callback_data=PackActionCallback(action="custom"),
    )
    builder.button(
        text="« Вернуться назад",
        callback_data=PackActionCallback(action="cancel"),
    )
    builder.adjust(1)

    return builder.as_markup()
