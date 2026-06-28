"""
Aros Market Telegram Bot — asosiy ishga tushirish fayli.
"""

import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import settings
from handlers import auth, cart, search, start
from storage import JSONFileStorage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=JSONFileStorage(path="fsm_storage.json"))

    # Handlerlar tartibi muhim: auth va cart search'dan oldin
    dp.include_router(start.router)
    dp.include_router(auth.router)
    dp.include_router(cart.router)
    dp.include_router(search.router)

    logger.info("🛒 Aros Market Bot ishga tushdi!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
