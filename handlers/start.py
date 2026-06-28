"""
/start va /help buyruqlari handleri.
"""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router(name="start")

WELCOME_TEXT = """
👋 <b>Aros Market botiga xush kelibsiz!</b>

Bu bot orqali <b>aros.uz</b> do'konidagi mahsulotlarni qidirishingiz mumkin.

🔍 <b>Qidiruv:</b> Mahsulot nomini yozing
<i>Masalan: "samsung", "kiyim", "poyafzal"</i>

📦 Natijalar ro'yxatidan mahsulotni tanlang va batafsil ma'lumot oling.
""".strip()


@router.message(Command("start", "help"))
async def handle_start(message: Message) -> None:
    """Botni ishga tushirish va yordam xabari."""
    await message.answer(WELCOME_TEXT)
