import asyncio
import gzip
import io
import uuid
from typing import Any, Dict, List, Optional, Tuple
from aiogram import Bot
from aiogram.types import BufferedInputFile, Document, InputSticker, Sticker
from src.core.logger import logger
from src.engine.color_utils import json_loads
from src.engine.lottie_compress import compress_tgs
from src.engine.lottie_engine import tint_lottie
from src.engine.text_engine import modify_lottie_text
from src.engine.webp_engine import tint_image


class StickerService:
    """Сервис обработки стикеров и управления стикерпаками."""

    def __init__(self):
        # Хранилище сессий пользователей в памяти: user_id -> data
        self._user_sessions: Dict[int, Dict[str, Any]] = {}
        # История цветов: user_id -> List[str]
        self._color_history: Dict[int, List[str]] = {}

    def get_session(self, user_id: int) -> Dict[str, Any]:
        if user_id not in self._user_sessions:
            self._user_sessions[user_id] = {
                "active_zone": "body",
                "zones": {"stroke": None, "body": None, "text": None},
                "raw_data": None,
                "is_animated": True,
                "is_emoji": False,
                "emoji_char": "🎨",
                "last_result": None,
                "pack_title": None,
                "pack_name": None,
            }
        return self._user_sessions[user_id]

    def reset_session(self, user_id: int) -> None:
        if user_id in self._user_sessions:
            del self._user_sessions[user_id]

    def record_color(self, user_id: int, hex_color: str) -> None:
        """Сохраняет цвет в недавнюю историю пользователя."""
        c = hex_color.upper()
        history = self._color_history.setdefault(user_id, [])
        if c in history:
            history.remove(c)
        history.insert(0, c)
        self._color_history[user_id] = history[:6]

    def get_history(self, user_id: int) -> List[str]:
        return self._color_history.get(user_id, [])

    async def download_sticker(self, bot: Bot, file_id: str) -> bytes:
        """Скачивает файл стикера из Telegram."""
        file_io = io.BytesIO()
        await bot.download(file_id, destination=file_io)
        return file_io.getvalue()

    async def process_recolor(
        self,
        raw_data: bytes,
        colors: Any,
        is_animated: bool,
        is_emoji: bool = False,
    ) -> bytes:
        """Асинхронная перекраска в отдельном потоке."""

        def _sync_worker() -> bytes:
            if is_animated:
                # Распаковка TGS (gzip JSON)
                decompressed = gzip.decompress(raw_data)
                lottie_dict = json_loads(decompressed)
                tinted = tint_lottie(lottie_dict, colors)
                return compress_tgs(tinted)
            else:
                return tint_image(raw_data, colors, is_emoji=is_emoji)

        return await asyncio.to_thread(_sync_worker)

    async def process_text_replace(
        self,
        raw_data: bytes,
        new_text: str,
        scale_factor: float = 1.0,
    ) -> bytes:
        """Асинхронная замена текста в Lottie."""

        def _sync_worker() -> bytes:
            decompressed = gzip.decompress(raw_data)
            lottie_dict = json_loads(decompressed)
            modify_lottie_text(lottie_dict, new_text, scale_factor=scale_factor)
            return compress_tgs(lottie_dict)

        return await asyncio.to_thread(_sync_worker)

    async def create_or_add_pack(
        self,
        bot: Bot,
        user_id: int,
        title: str,
        short_name: str,
        sticker_data: bytes,
        is_animated: bool,
        is_emoji: bool,
        emoji_char: str = "🎨",
    ) -> Tuple[Optional[str], Optional[str]]:
        """Создает новый стикерпак или добавляет стикер в существующий.

        Возвращает (pack_url, error_message).
        """
        me = await bot.get_me()
        bot_username = me.username or str(me.id)

        # short_name должен оканчиваться на _by_<bot_username>
        full_short_name = f"{short_name}_by_{bot_username}"
        fmt = "animated" if is_animated else "static"
        ext = "tgs" if is_animated else "webp"
        sticker_type = "custom_emoji" if is_emoji else "regular"

        input_file = BufferedInputFile(sticker_data, filename=f"sticker.{ext}")
        input_sticker = InputSticker(
            sticker=input_file,
            emoji_list=[emoji_char],
            format=fmt,
        )

        try:
            # Сначала пытаемся создать новый набор
            await bot.create_new_sticker_set(
                user_id=user_id,
                name=full_short_name,
                title=title,
                stickers=[input_sticker],
                sticker_type=sticker_type,
            )
            prefix = "addemoji" if is_emoji else "addstickers"
            return f"https://t.me/{prefix}/{full_short_name}", None
        except Exception as e:
            err_msg = str(e).lower()
            if "already exists" in err_msg or "short_name_occupied" in err_msg:
                # Пак уже существует — добавляем стикер
                try:
                    await bot.add_sticker_to_set(
                        user_id=user_id,
                        name=full_short_name,
                        sticker=input_sticker,
                    )
                    prefix = "addemoji" if is_emoji else "addstickers"
                    return f"https://t.me/{prefix}/{full_short_name}", None
                except Exception as add_err:
                    logger.exception(f"Не удалось добавить стикер в {full_short_name}: {add_err}")
                    return None, f"Ошибка добавления в пак: {add_err}"
            else:
                logger.exception(f"Ошибка создания стикерпака: {e}")
                return None, f"Ошибка Telegram API: {e}"


sticker_service = StickerService()
