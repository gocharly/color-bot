from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from src.core.constants import MAX_CUSTOM_TEXT_LENGTH
from src.core.typography import make_card, make_status_card
from src.keyboards.callbacks import ActionCallback
from src.keyboards.inline_keyboards import get_result_keyboard
from src.services.sticker_service import sticker_service
from src.states.recolor_states import RecolorStates

router = Router(name="text_replace_router")


@router.callback_query(ActionCallback.filter(F.action == "change_text"))
async def handle_change_text_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    """Запрос ввода текста для замены в анимированном стикере."""
    user_id = callback.from_user.id
    session = sticker_service.get_session(user_id)

    if not session.get("is_animated"):
        await callback.answer(
            "Замена текста поддерживается только для анимированных (векторных TGS) стикеров.",
            show_alert=True,
        )
        return

    await state.set_state(RecolorStates.entering_custom_text)
    card = make_card(
        title="Замена текста в стикере",
        params={
            "Лимит": f"до {MAX_CUSTOM_TEXT_LENGTH} символов",
            "Шрифт": "Comfortaa Bold (округлый)",
        },
        footer=(
            "Напиши в ответ любое слово, никнейм или фразу, и я впишу её прямо в анимацию стикера!\n\n"
            "<i>Отправь сообщение с текстом:</i>"
        ),
    )
    await callback.message.edit_text(card, parse_mode="HTML")


@router.message(RecolorStates.entering_custom_text)
async def process_custom_text_input(message: Message, state: FSMContext) -> None:
    """Обработка введенного текста и векторизация глифов в Lottie."""
    user_id = message.from_user.id
    session = sticker_service.get_session(user_id)
    raw_data = session.get("last_result") or session.get("raw_data")

    if not raw_data or not session.get("is_animated"):
        await state.clear()
        await message.answer(
            make_status_card("Сессия завершилась", "Пожалуйста, отправь анимированный стикер заново.", is_error=True),
            parse_mode="HTML",
        )
        return

    text = (message.text or "").strip()
    if not text:
        await message.answer(
            make_status_card("Пустой текст", "Пожалуйста, напиши хотя бы одно слово.", is_error=True),
            parse_mode="HTML",
        )
        return

    if len(text) > MAX_CUSTOM_TEXT_LENGTH:
        await message.answer(
            make_status_card(
                "Слишком длинный текст",
                f"Чтобы надпись красиво поместилась в стикер, длина должна быть до {MAX_CUSTOM_TEXT_LENGTH} символов.",
                is_error=True,
            ),
            parse_mode="HTML",
        )
        return

    await state.clear()

    wait_msg = await message.answer(
        make_status_card("Создание надписи", f"Векторизую текст «{text}» шрифтом Comfortaa..."),
        parse_mode="HTML",
    )

    try:
        patched_bytes = await sticker_service.process_text_replace(
            raw_data=raw_data,
            new_text=text,
        )
        session["last_result"] = patched_bytes

        card = make_card(
            title="Надпись успешно добавлена",
            params={
                "Текст": text,
                "Формат": "Анимированный стикер (TGS)",
                "Размер": f"{len(patched_bytes) / 1024:.1f} КБ",
            },
            footer="Готово! Выбери, что сделать с полученным стикером:",
        )
        await wait_msg.edit_text(card, reply_markup=get_result_keyboard(), parse_mode="HTML")
    except Exception as e:
        await wait_msg.edit_text(
            make_status_card("Ошибка создания", f"Не удалось обновить текст: {e}", is_error=True),
            parse_mode="HTML",
        )
