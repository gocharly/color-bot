from typing import List, Optional
from aiogram import Bot, F, Router
from aiogram.types import Document, Message, MessageEntity, Sticker
from src.core.logger import logger
from src.core.typography import make_card, make_status_card
from src.keyboards.inline_keyboards import get_color_palette_keyboard
from src.services.sticker_service import sticker_service

router = Router(name="sticker_router")


async def _process_sticker_object(message: Message, bot: Bot, st: Sticker, wait_msg: Message) -> None:
    """Общий обработчик для стикеров и кастомных эмодзи."""
    user_id = message.from_user.id

    if st.is_video:
        await wait_msg.edit_text(
            make_status_card(
                "Видеостикеры пока не поддерживаются",
                "Этот элемент использует видеопоток (.webm).\n\n"
                "Telegram поддерживает перекраску векторных анимированных стикеров (.tgs) и статичных (.webp). Пожалуйста, пришли векторный стикер или эмодзи из векторного набора!",
                is_error=True,
            ),
            parse_mode="HTML",
        )
        return

    try:
        raw_data = await sticker_service.download_sticker(bot, st.file_id)
    except Exception as e:
        logger.exception(f"Ошибка загрузки стикера: {e}")
        await wait_msg.edit_text(
            make_status_card("Не удалось скачать стикер", f"Ошибка связи с Telegram: {e}", is_error=True),
            parse_mode="HTML",
        )
        return

    session = sticker_service.get_session(user_id)
    session["raw_data"] = raw_data
    session["is_animated"] = bool(st.is_animated)
    session["is_emoji"] = bool(st.type == "custom_emoji" or getattr(st, "custom_emoji_id", None))
    session["emoji_char"] = st.emoji or "🎨"
    session["zones"] = {"stroke": None, "body": None, "text": None}
    session["active_zone"] = "body"

    fmt_label = "Анимированный вектор (TGS)" if st.is_animated else "Обычный статичный (WebP)"
    type_label = "Кастомный эмодзи" if session["is_emoji"] else "Стикер"

    card = make_card(
        title=f"{type_label} успешно загружен",
        params={
            "Тип": fmt_label,
            "Эмодзи": session["emoji_char"],
            "Размер": f"{len(raw_data) / 1024:.1f} КБ",
        },
        footer=(
            "Какой цвет выберем? Нажми на понравившийся оттенок ниже.\n"
            "Если нужен точный тон — используй кнопку «Свой оттенок (HEX)»."
        ),
    )

    history = sticker_service.get_history(user_id)
    kb = get_color_palette_keyboard(
        active_zone="body",
        recent_colors=history,
        is_animated=bool(st.is_animated),
    )

    await wait_msg.edit_text(card, reply_markup=kb, parse_mode="HTML")


@router.message(F.sticker)
async def handle_sticker(message: Message, bot: Bot) -> None:
    """Обработка полученного стикера."""
    wait_msg = await message.answer(
        make_status_card("Загрузка", "Секундочку, считываю детали стикера..."),
        parse_mode="HTML",
    )
    await _process_sticker_object(message, bot, message.sticker, wait_msg)


@router.message(F.document)
async def handle_document(message: Message, bot: Bot) -> None:
    """Обработка документов .tgs и .webp."""
    doc: Document = message.document
    fn = (doc.file_name or "").lower()
    mime = (doc.mime_type or "").lower()
    user_id = message.from_user.id

    is_tgs = fn.endswith(".tgs") or mime == "application/x-tgsticker"
    is_webp = fn.endswith(".webp") or mime == "image/webp"

    if not (is_tgs or is_webp):
        return

    wait_msg = await message.answer(
        make_status_card("Загрузка", "Получаю файл..."),
        parse_mode="HTML",
    )

    try:
        raw_data = await sticker_service.download_sticker(bot, doc.file_id)
    except Exception as e:
        await wait_msg.edit_text(
            make_status_card("Не удалось загрузить файл", str(e), is_error=True),
            parse_mode="HTML",
        )
        return

    session = sticker_service.get_session(user_id)
    session["raw_data"] = raw_data
    session["is_animated"] = is_tgs
    session["is_emoji"] = False
    session["emoji_char"] = "🎨"
    session["zones"] = {"stroke": None, "body": None, "text": None}
    session["active_zone"] = "body"

    fmt_label = "Векторный файл (TGS)" if is_tgs else "Растровый файл (WebP)"
    card = make_card(
        title="Файл стикера загружен",
        params={
            "Файл": doc.file_name or "sticker",
            "Тип": fmt_label,
            "Размер": f"{len(raw_data) / 1024:.1f} КБ",
        },
        footer="Выбери цвет в палитре ниже:",
    )

    history = sticker_service.get_history(user_id)
    kb = get_color_palette_keyboard(
        active_zone="body",
        recent_colors=history,
        is_animated=is_tgs,
    )

    await wait_msg.edit_text(card, reply_markup=kb, parse_mode="HTML")


@router.message(F.text | F.caption)
async def handle_custom_emoji_or_text(message: Message, bot: Bot) -> None:
    """Обработка сообщений с кастомными анимированными эмодзи."""
    # Поиск entities типа custom_emoji в тексте или подписи
    entities: List[MessageEntity] = (message.entities or []) + (message.caption_entities or [])
    custom_ids = [e.custom_emoji_id for e in entities if e.type == "custom_emoji" and e.custom_emoji_id]

    if custom_ids:
        wait_msg = await message.answer(
            make_status_card("Загрузка", "Нашёл кастомный эмодзи, загружаю из Telegram..."),
            parse_mode="HTML",
        )
        try:
            stickers = await bot.get_custom_emoji_stickers(custom_emoji_ids=[custom_ids[0]])
            if stickers:
                await _process_sticker_object(message, bot, stickers[0], wait_msg)
                return
            else:
                await wait_msg.edit_text(
                    make_status_card(
                        "Эмодзи не найден",
                        "Telegram не вернул данные этого кастомного эмодзи. Попробуй отправить другой эмодзи или стикер.",
                        is_error=True,
                    ),
                    parse_mode="HTML",
                )
                return
        except Exception as e:
            logger.exception(f"Ошибка получения custom emoji: {e}")
            await wait_msg.edit_text(
                make_status_card("Ошибка загрузки", f"Не удалось загрузить кастомный эмодзи: {e}", is_error=True),
                parse_mode="HTML",
            )
            return

    # Если это обычный текст без эмодзи и не команда:
    text = (message.text or message.caption or "").strip()
    if text and not text.startswith("/"):
        await message.answer(
            make_status_card(
                "Как отправить стикер",
                "Отправь мне любой стикер или анимированный эмодзи из набора, и я помогу изменить его цвет под твой вкус!",
            ),
            parse_mode="HTML",
        )
