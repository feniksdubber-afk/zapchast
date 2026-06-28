"""
/start va /help buyruqlari.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

router = Router(name="start")

WELCOME_TEXT = """
👋 <b>Aros Market botiga xush kelibsiz!</b>

🔍 <b>Qidiruv:</b> Mahsulot nomini yozing
🛒 <b>Savat:</b> /cart
👤 <b>Kirish:</b> /login
👤 <b>Profil:</b> /profile
🚪 <b>Chiqish:</b> /logout
""".strip()


@router.message(Command("start", "help"))
async def handle_start(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    token = data.get("token")

    extra = "\n\n✅ Tizimga kirgansiz." if token else "\n\n⚠️ Savatga qo'shish uchun /login qiling."
    await message.answer(WELCOME_TEXT + extra)
