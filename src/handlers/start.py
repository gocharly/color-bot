from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from src.core.typography import make_card

router = Router(name="start_router")


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Понятное приветствие с описанием основных этапов."""
    card = make_card(
        title="Перекраска стикеров и эмодзи",
        footer=(
            "1. Отправь любой стикер или эмодзи (анимированный или обычный).\n"
            "2. Выбери оттенок в палитре или укажи свой HEX-код.\n"
            "3. Забери результат в чат или создай собственный пак.\n\n"
            "<i>Отправь стикер или эмодзи прямо сюда, чтобы начать.</i>"
        ),
    )
    await message.answer(card, parse_mode="HTML")


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Короткая и понятная справка."""
    card = make_card(
        title="Справка",
        footer=(
            "• Отправь стикер или эмодзи — появится палитра цветов.\n"
            "• Нажми на нужный оттенок или введи свой HEX-код.\n"
            "• Забери результат прямо в чат или создай пак."
        ),
    )
    await message.answer(card, parse_mode="HTML")
