from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from src.config import settings
from src.core.logger import logger
from src.handlers.pack import router as pack_router
from src.handlers.recolor import router as recolor_router
from src.handlers.start import router as start_router
from src.handlers.sticker import router as sticker_router
from src.handlers.text_replace import router as text_replace_router


def create_bot() -> Bot:
    """Создает экземпляр aiogram Bot."""
    return Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher() -> Dispatcher:
    """Создает и конфигурирует Dispatcher с подключенными роутерами."""
    dp = Dispatcher(storage=MemoryStorage())

    # Регистрация роутеров в логическом порядке
    dp.include_router(start_router)
    dp.include_router(sticker_router)
    dp.include_router(recolor_router)
    dp.include_router(text_replace_router)
    dp.include_router(pack_router)

    return dp


async def start_bot() -> None:
    """Главная точка входа для запуска бота в режиме polling."""
    if settings.bot_token == "YOUR_BOT_TOKEN_HERE" or not settings.bot_token:
        logger.error("ОШИБКА: Задайте валидный BOT_TOKEN в файле .env!")
        return

    bot = create_bot()
    dp = create_dispatcher()

    me = await bot.get_me()
    logger.info(f"Бот запущен: @{me.username} (ID: {me.id})")

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        logger.info("Сессия бота закрыта.")
