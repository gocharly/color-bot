from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from src.core.typography import make_card, make_status_card
from src.engine.color_utils import parse_hex_list
from src.keyboards.callbacks import ActionCallback, ColorCallback, ZoneCallback
from src.keyboards.inline_keyboards import (
    get_color_palette_keyboard,
    get_result_keyboard,
    get_zones_keyboard,
)
from src.services.sticker_service import sticker_service
from src.states.recolor_states import RecolorStates

router = Router(name="recolor_router")


def _get_item_terms(session: dict) -> tuple[str, str]:
    """Возвращает названия элемента в именительном и творительном падежах."""
    if session.get("is_emoji"):
        return "Эмодзи", "с эмодзи"
    return "Стикер", "со стикером"


@router.callback_query(ColorCallback.filter())
async def handle_color_selection(callback: CallbackQuery, callback_data: ColorCallback) -> None:
    """Обработка выбора цвета из палитры с мягким дружелюбным статусом."""
    user_id = callback.from_user.id
    session = sticker_service.get_session(user_id)
    raw_data = session.get("raw_data")

    item_name, item_genitive = _get_item_terms(session)

    if not raw_data:
        await callback.answer(f"Сессия завершилась. Пожалуйста, отправь {item_name.lower()} ещё раз.", show_alert=True)
        return

    selected_hex = callback_data.hex.upper()
    zone = callback_data.zone

    if zone in session["zones"]:
        session["zones"][zone] = selected_hex
    else:
        session["zones"]["body"] = selected_hex

    sticker_service.record_color(user_id, selected_hex)

    await callback.message.edit_text(
        make_status_card("Обработка", f"Секундочку, перекрашиваю в {selected_hex}..."),
        parse_mode="HTML",
    )

    try:
        active_zones = session["zones"]
        has_multi = any(v is not None for k, v in active_zones.items() if k != zone)
        colors_to_apply = active_zones if has_multi else selected_hex

        result_bytes = await sticker_service.process_recolor(
            raw_data=raw_data,
            colors=colors_to_apply,
            is_animated=session["is_animated"],
            is_emoji=session["is_emoji"],
        )
        session["last_result"] = result_bytes
        session["last_color"] = selected_hex

        is_em = session.get("is_emoji", False)
        type_desc = "Кастомный анимированный эмодзи" if is_em else ("Векторный анимированный" if session["is_animated"] else "Статичный растровый")

        card = make_card(
            title=f"{item_name} успешно перекрашен",
            params={
                "Цвет": selected_hex,
                "Формат": type_desc,
                "Размер": f"{len(result_bytes) / 1024:.1f} КБ",
            },
            footer=f"Готово! Что сделаем {item_genitive} дальше?",
        )
        await callback.message.edit_text(
            card,
            reply_markup=get_result_keyboard(is_emoji=is_em),
            parse_mode="HTML",
        )
    except Exception as e:
        await callback.message.edit_text(
            make_status_card("Не удалось перекрасить", f"Произошла ошибка: {e}", is_error=True),
            parse_mode="HTML",
        )


@router.callback_query(ActionCallback.filter(F.action == "instant_sticker"))
async def handle_send_sticker(callback: CallbackQuery, bot: Bot) -> None:
    """Отправляет готовый перекрашенный стикер или эмодзи прямо в чат."""
    user_id = callback.from_user.id
    session = sticker_service.get_session(user_id)
    data = session.get("last_result")
    item_name, _ = _get_item_terms(session)

    if not data:
        await callback.answer(f"{item_name} не найден. Выбери оттенок заново.", show_alert=True)
        return

    ext = "tgs" if session["is_animated"] else "webp"
    st_file = BufferedInputFile(data, filename=f"sticker.{ext}")

    await bot.send_sticker(
        chat_id=callback.message.chat.id,
        sticker=st_file,
    )
    await callback.answer(f"{item_name} отправлен в чат!")


@router.callback_query(ActionCallback.filter(F.action == "send_file"))
async def handle_send_file(callback: CallbackQuery, bot: Bot) -> None:
    """Отправляет файл документом."""
    user_id = callback.from_user.id
    session = sticker_service.get_session(user_id)
    data = session.get("last_result")
    item_name, _ = _get_item_terms(session)

    if not data:
        await callback.answer(f"{item_name} не найден.", show_alert=True)
        return

    ext = "tgs" if session["is_animated"] else "webp"
    doc_file = BufferedInputFile(data, filename=f"recolored_{item_name.lower()}.{ext}")

    await bot.send_document(
        chat_id=callback.message.chat.id,
        document=doc_file,
        caption=f"Перекрашенный исходный файл ({item_name.lower()})",
    )
    await callback.answer("Файл отправлен")


@router.callback_query(ActionCallback.filter(F.action == "zones_menu"))
async def handle_zones_menu(callback: CallbackQuery) -> None:
    """Открытие меню зон для раздельной перекраски."""
    user_id = callback.from_user.id
    session = sticker_service.get_session(user_id)
    item_name, _ = _get_item_terms(session)

    card = make_card(
        title="Настройка раздельных зон",
        params={
            "Контур (обводка)": session["zones"].get("stroke") or "исходный",
            "Тело (заливка)": session["zones"].get("body") or "исходное",
            "Детали и текст": session["zones"].get("text") or "исходные",
        },
        footer=(
            f"Здесь можно раскрасить {item_name.lower()} в несколько цветов одновременно.\n"
            "Нажми на нужную часть, чтобы выбрать для неё оттенок из палитры, а затем нажми «Готово, применить цвета»."
        ),
    )
    await callback.message.edit_text(
        card,
        reply_markup=get_zones_keyboard(session["zones"], is_emoji=session.get("is_emoji", False)),
        parse_mode="HTML",
    )


@router.callback_query(ActionCallback.filter(F.action == "render_zones"))
async def handle_render_zones(callback: CallbackQuery) -> None:
    """Применение выбранных зон."""
    user_id = callback.from_user.id
    session = sticker_service.get_session(user_id)
    raw_data = session.get("raw_data")
    item_name, _ = _get_item_terms(session)

    if not raw_data:
        await callback.answer(f"Сессия устарела. Отправь {item_name.lower()} снова.", show_alert=True)
        return

    await callback.message.edit_text(
        make_status_card("Обработка", "Применяю цвета ко всем зонам..."),
        parse_mode="HTML",
    )

    try:
        result_bytes = await sticker_service.process_recolor(
            raw_data=raw_data,
            colors=session["zones"],
            is_animated=session["is_animated"],
            is_emoji=session["is_emoji"],
        )
        session["last_result"] = result_bytes

        is_em = session.get("is_emoji", False)
        card = make_card(
            title=f"{item_name} с зонами готов",
            params={
                "Контур": session["zones"].get("stroke") or "исходный",
                "Тело": session["zones"].get("body") or "исходное",
                "Детали": session["zones"].get("text") or "исходные",
                "Размер": f"{len(result_bytes) / 1024:.1f} КБ",
            },
            footer="Всё готово! Выбери действие:",
        )
        await callback.message.edit_text(
            card,
            reply_markup=get_result_keyboard(is_emoji=is_em),
            parse_mode="HTML",
        )
    except Exception as e:
        await callback.message.edit_text(
            make_status_card("Ошибка перекраски", str(e), is_error=True),
            parse_mode="HTML",
        )


@router.callback_query(ZoneCallback.filter())
async def handle_zone_pick(callback: CallbackQuery, callback_data: ZoneCallback) -> None:
    """Переход к выбору цвета для конкретной зоны."""
    user_id = callback.from_user.id
    session = sticker_service.get_session(user_id)
    session["active_zone"] = callback_data.zone

    zone_names = {
        "all": "весь элемент целиком",
        "body": "основное тело",
        "stroke": "контур (обводка)",
        "text": "мелкие детали и текст",
    }
    name = zone_names.get(callback_data.zone, callback_data.zone)

    card = make_card(
        title=f"Цвет для зоны: {name}",
        footer="Выбери цвет в палитре ниже:",
    )
    history = sticker_service.get_history(user_id)
    kb = get_color_palette_keyboard(
        active_zone=callback_data.zone,
        recent_colors=history,
        is_animated=session["is_animated"],
    )
    await callback.message.edit_text(card, reply_markup=kb, parse_mode="HTML")


@router.callback_query(ActionCallback.filter(F.action == "back_to_palette"))
async def handle_back_to_palette(callback: CallbackQuery) -> None:
    """Возврат к основной палитре."""
    user_id = callback.from_user.id
    session = sticker_service.get_session(user_id)
    item_name, _ = _get_item_terms(session)

    card = make_card(
        title="Палитра цветов",
        footer=f"Выбери цвет для {item_name.lower()}:",
    )
    history = sticker_service.get_history(user_id)
    kb = get_color_palette_keyboard(
        active_zone="body",
        recent_colors=history,
        is_animated=session.get("is_animated", True),
    )
    await callback.message.edit_text(card, reply_markup=kb, parse_mode="HTML")


@router.callback_query(ActionCallback.filter(F.action == "custom_hex"))
async def handle_custom_hex_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    """Запрос ввода собственного HEX-кода."""
    await state.set_state(RecolorStates.entering_custom_hex)
    card = make_card(
        title="Ввод своего оттенка (HEX)",
        params={
            "Один оттенок": "#007AFF",
            "Два цвета (контур + тело)": "#007AFF #1C1C1E",
            "Три цвета (контур + тело + текст)": "#007AFF #1C1C1E #F2F2F7",
        },
        footer=(
            "Просто отправь мне в ответ сообщение с кодом цвета (можно без знака #).\n"
            "Например: <code>#34C759</code> или <code>FF5500</code>"
        ),
    )
    await callback.message.edit_text(card, parse_mode="HTML")


@router.message(RecolorStates.entering_custom_hex)
async def process_custom_hex_input(message: Message, state: FSMContext) -> None:
    """Обработка пользовательского текста с HEX-кодами."""
    user_id = message.from_user.id
    session = sticker_service.get_session(user_id)
    raw_data = session.get("raw_data")
    item_name, _ = _get_item_terms(session)

    if not raw_data:
        await state.clear()
        await message.answer(
            make_status_card("Сессия устарела", f"Пожалуйста, отправь {item_name.lower()} заново, чтобы продолжить.", is_error=True),
            parse_mode="HTML",
        )
        return

    hexes = parse_hex_list(message.text or "")
    if not hexes:
        await message.answer(
            make_status_card(
                "Не удалось распознать цвет",
                "Пожалуйста, введи корректный 6-значный HEX код цвета, например <code>#FF3B30</code> или <code>007AFF</code>.",
                is_error=True,
            ),
            parse_mode="HTML",
        )
        return

    await state.clear()

    wait_msg = await message.answer(
        make_status_card("Обработка", f"Применяю {' '.join(hexes)}..."),
        parse_mode="HTML",
    )

    try:
        result_bytes = await sticker_service.process_recolor(
            raw_data=raw_data,
            colors=hexes,
            is_animated=session["is_animated"],
            is_emoji=session["is_emoji"],
        )
        session["last_result"] = result_bytes
        session["last_color"] = hexes[0]
        sticker_service.record_color(user_id, hexes[0])

        is_em = session.get("is_emoji", False)
        type_desc = "Кастомный анимированный эмодзи" if is_em else ("Векторный анимированный" if session["is_animated"] else "Статичный растровый")

        card = make_card(
            title=f"{item_name} готов",
            params={
                "Цвета": " ".join(hexes),
                "Формат": type_desc,
                "Размер": f"{len(result_bytes) / 1024:.1f} КБ",
            },
            footer="Выбери действие с результатом:",
        )
        await wait_msg.edit_text(card, reply_markup=get_result_keyboard(is_emoji=is_em), parse_mode="HTML")
    except Exception as e:
        await wait_msg.edit_text(
            make_status_card("Ошибка перекраски", str(e), is_error=True),
            parse_mode="HTML",
        )
