import asyncio
import sys
from src.bot import start_bot
from src.core.logger import logger

if __name__ == "__main__":
    try:
        asyncio.run(start_bot())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен пользователем.")
    except Exception as e:
        logger.exception(f"Критическая ошибка работы бота: {e}")
        sys.exit(1)
