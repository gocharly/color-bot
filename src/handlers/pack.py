import re
import uuid
from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from src.core.typography import make_card, make_status_card
from src.keyboards.callbacks import ActionCallback, PackActionCallback
from src.keyboards.inline_keyboards import get_pack_creation_keyboard, get_result_keyboard
from src.services.sticker_service import sticker_service
from src.states.recolor_states import RecolorStates

router = Router(name="pack_router")


@router.callback_query(ActionCallback.filter(F.action == "add_pack"))
async def handle_add_pack_prompt(callback: CallbackQuery) -> None:
    """Запрос на создание или добавление в стикерпак / эмодзи-пак."""
    user_id = callback.from_user.id
    session = sticker_service.get_session(user_id)
    is_em = session.get("is_emoji", False)
    pack_name = "эмодзи-пака" if is_em else "стикерпака"

    card = make_card(
        title=f"Создание {pack_name}",
        params={
            "В 1 клик": "Сам придумаю название и создам набор",
            "Своё имя": "Ты сам выберешь название и ссылку",
        },
        footer=f"Как создадим {pack_name}?",
    )
    await callback.message.edit_text(card, reply_markup=get_pack_creation_keyboard(is_emoji=is_em), parse_mode="HTML")


@router.callback_query(PackActionCallback.filter(F.action == "auto"))
async def handle_pack_auto(callback: CallbackQuery, bot: Bot) -> None:
    """Автоматическое создание стикерпака или эмодзи-пака с понятным отчётом."""
    user_id = callback.from_user.id
    session = sticker_service.get_session(user_id)
    data = session.get("last_result")
    is_em = session.get("is_emoji", False)
    item_label = "эмодзи" if is_em else "стикер"
    pack_label = "эмодзи-пак" if is_em else "стикерпак"

    if not data:
        await callback.answer(f"Сессия завершилась. Пожалуйста, перекрась {item_label} заново.", show_alert=True)
        return

    color_tag = session.get("last_color", "color").replace("#", "")
    prefix = "em_" if is_em else ""
    short_name = f"color_{prefix}{color_tag.lower()}_{uuid.uuid4().hex[:6]}"
    title = f"Color Bot {'Emojis' if is_em else ''} {session.get('last_color', '')}".strip()

    await callback.message.edit_text(
        make_status_card("Публикация", f"Минутку, регистрирую {pack_label} в Telegram..."),
        parse_mode="HTML",
    )

    pack_url, err = await sticker_service.create_or_add_pack(
        bot=bot,
        user_id=user_id,
        title=title,
        short_name=short_name,
        sticker_data=data,
        is_animated=session["is_animated"],
        is_emoji=session["is_emoji"],
        emoji_char=session.get("emoji_char", "🎨"),
    )

    if err or not pack_url:
        await callback.message.edit_text(
            make_status_card(f"Не удалось создать {pack_label}", err or "Неизвестная ошибка Telegram API", is_error=True),
            parse_mode="HTML",
        )
        return

    title_done = "Эмодзи-пак готов" if is_em else "Стикерпак готов"
    footer_desc = (
        f"Набор эмодзи успешно зарегистрирован в Telegram!\n\n"
        f"<b>Ссылка для добавления в панель эмодзи:</b>\n<a href=\"{pack_url}\">{pack_url}</a>\n\n"
        f"Нажми на ссылку, чтобы установить эмодзи-пак и вставлять этот эмодзи прямо в текст любых сообщений!"
        if is_em
        else f"Набор успешно зарегистрирован в Telegram!\n\n"
        f"<b>Ссылка для добавления:</b>\n<a href=\"{pack_url}\">{pack_url}</a>\n\n"
        f"Нажми на ссылку, чтобы установить стикерпак себе или переслать друзьям."
    )

    card = make_card(
        title=title_done,
        params={
            "Название": title,
            "Ссылка": pack_url,
        },
        footer=footer_desc,
    )
    await callback.message.edit_text(card, reply_markup=get_result_keyboard(is_emoji=is_em, has_pack=True), parse_mode="HTML")


@router.callback_query(PackActionCallback.filter(F.action == "custom"))
async def handle_pack_custom_title_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    """Запрос ввода собственного названия стикерпака / эмодзи-пака."""
    user_id = callback.from_user.id
    session = sticker_service.get_session(user_id)
    is_em = session.get("is_emoji", False)
    pack_name = "эмодзи-пака" if is_em else "стикерпака"

    await state.set_state(RecolorStates.entering_pack_title)
    card = make_card(
        title=f"Название для {pack_name}",
        footer=f"Напиши отображаемое название для своего набора (например: «Мои {'неоновые эмодзи' if is_em else 'неоновые стикеры'}»):",
    )
    await callback.message.edit_text(card, parse_mode="HTML")


@router.message(RecolorStates.entering_pack_title)
async def process_pack_title_input(message: Message, state: FSMContext) -> None:
    """Сохранение названия и запрос короткой ссылки."""
    title = (message.text or "").strip()
    if not title or len(title) > 64:
        await message.answer(
            make_status_card("Ошибка в названии", "Название должно быть длиной от 1 до 64 символов.", is_error=True),
            parse_mode="HTML",
        )
        return

    user_id = message.from_user.id
    session = sticker_service.get_session(user_id)
    session["pack_title"] = title
    is_em = session.get("is_emoji", False)

    await state.set_state(RecolorStates.entering_pack_shortname)
    link_prefix = "t.me/addemoji/..." if is_em else "t.me/addstickers/..."
    card = make_card(
        title="Короткая ссылка (short_name)",
        params={
            "Выбранное название": title,
            "Правила": "Только латинские буквы, цифры и подчеркивание (например: my_cool_pack)",
        },
        footer=f"Напиши короткое слово для ссылки вида {link_prefix} :",
    )
    await message.answer(card, parse_mode="HTML")


@router.message(RecolorStates.entering_pack_shortname)
async def process_pack_shortname_input(message: Message, state: FSMContext, bot: Bot) -> None:
    """Создание пака с пользовательским short_name."""
    raw_name = (message.text or "").strip().lower()
    if not re.fullmatch(r"[a-z0-9_]{3,32}", raw_name):
        await message.answer(
            make_status_card(
                "Неподходящее имя ссылки",
                "Имя ссылки должно содержать от 3 до 32 символов (только латиница a-z, цифры 0-9 и '_'). Попробуй ещё раз:",
                is_error=True,
            ),
            parse_mode="HTML",
        )
        return

    await state.clear()
    user_id = message.from_user.id
    session = sticker_service.get_session(user_id)
    data = session.get("last_result")
    is_em = session.get("is_emoji", False)
    default_title = "Color Bot Emojis" if is_em else "Color Bot Pack"
    title = session.get("pack_title", default_title)
    pack_label = "эмодзи-пак" if is_em else "стикерпак"

    if not data:
        await message.answer(
            make_status_card("Сессия завершилась", "Данные устарели. Пожалуйста, начни заново.", is_error=True),
            parse_mode="HTML",
        )
        return

    wait_msg = await message.answer(
        make_status_card("Публикация", f"Создаю {pack_label} «{title}»..."),
        parse_mode="HTML",
    )

    pack_url, err = await sticker_service.create_or_add_pack(
        bot=bot,
        user_id=user_id,
        title=title,
        short_name=raw_name,
        sticker_data=data,
        is_animated=session["is_animated"],
        is_emoji=session["is_emoji"],
        emoji_char=session.get("emoji_char", "🎨"),
    )

    if err or not pack_url:
        await wait_msg.edit_text(
            make_status_card(f"Не удалось создать {pack_label}", err or "Неизвестная ошибка Telegram API", is_error=True),
            parse_mode="HTML",
        )
        return

    title_done = "Эмодзи-пак готов" if is_em else "Стикерпак готов"
    footer_desc = (
        f"Набор эмодзи успешно зарегистрирован в Telegram!\n\n"
        f"<b>Ссылка для добавления в панель эмодзи:</b>\n<a href=\"{pack_url}\">{pack_url}</a>\n\n"
        f"Нажми на ссылку, чтобы установить эмодзи-пак и вставлять этот эмодзи прямо в текст любых сообщений!"
        if is_em
        else f"Набор успешно создан в Telegram!\n\n"
        f"<b>Ссылка для добавления:</b>\n<a href=\"{pack_url}\">{pack_url}</a>\n\n"
        f"Перейди по ссылке, чтобы добавить стикеры к себе или переслать друзьям."
    )

    card = make_card(
        title=title_done,
        params={
            "Название": title,
            "Ссылка": pack_url,
        },
        footer=footer_desc,
    )
    await wait_msg.edit_text(card, reply_markup=get_result_keyboard(is_emoji=is_em, has_pack=True), parse_mode="HTML")


@router.callback_query(PackActionCallback.filter(F.action == "cancel"))
async def handle_pack_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """Отмена создания пака и возврат к результату."""
    await state.clear()
    user_id = callback.from_user.id
    session = sticker_service.get_session(user_id)
    is_em = session.get("is_emoji", False)
    item_name = "Эмодзи" if is_em else "Стикер"

    await callback.message.edit_text(
        make_card(
            title=f"{item_name} готов",
            footer=f"Выбери действие с полученным {item_name.lower()}:",
        ),
        reply_markup=get_result_keyboard(is_emoji=is_em),
        parse_mode="HTML",
    )
