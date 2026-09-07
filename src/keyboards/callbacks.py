from typing import Optional
from aiogram.filters.callback_data import CallbackData


class ColorCallback(CallbackData, prefix="col"):
    """Выбор цвета из палитры."""

    hex: str
    zone: str = "body"


class ZoneCallback(CallbackData, prefix="zon"):
    """Выбор зоны редактирования стикера."""

    zone: str


class ActionCallback(CallbackData, prefix="act"):
    """Общие действия пользователя."""

    action: str  # instant_sticker, send_file, save_pack, custom_hex, change_text, cancel, back


class PackActionCallback(CallbackData, prefix="pck"):
    """Действия по созданию/добавлению в стикерпак."""

    action: str  # auto, custom, cancel
