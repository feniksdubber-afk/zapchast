"""
Login / autentifikatsiya handlerlari.
Telefon → SMS → Token → Profil ko'rish
"""

import logging
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

from services.api_client import ArosAPIError, get_api_client
from utils.formatting import format_price

logger = logging.getLogger(__name__)
router = Router(name="auth")


class LoginState(StatesGroup):
    waiting_phone = State()   # Telefon raqam kutilmoqda
    waiting_code  = State()   # SMS kod kutilmoqda


def _phone_keyboard() -> ReplyKeyboardMarkup:
    """Telefon raqamni yuborish uchun tugma."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Raqamimni yuborish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


# ─── /login buyrug'i ─────────────────────────────────────────────────────────

@router.message(Command("login"))
async def cmd_login(message: Message, state: FSMContext) -> None:
    # Allaqachon login qilinganmi?
    data = await state.get_data()
    if data.get("token"):
        await message.answer(
            "✅ Siz allaqachon tizimga kirgansiz.\n"
            "Profilni ko'rish: /profile\n"
            "Chiqish: /logout"
        )
        return

    await state.set_state(LoginState.waiting_phone)
    await message.answer(
        "📱 Telefon raqamingizni yuboring:\n\n"
        "Tugma orqali yoki qo'lda yozing: <code>+998901234567</code>",
        reply_markup=_phone_keyboard(),
    )


# ─── Telefon qabul qilish (contact yoki matn) ────────────────────────────────

@router.message(LoginState.waiting_phone, F.contact)
async def handle_contact(message: Message, state: FSMContext) -> None:
    phone = message.contact.phone_number
    if not phone.startswith("+"):
        phone = "+" + phone
    await _send_sms(message, state, phone)


@router.message(LoginState.waiting_phone, F.text)
async def handle_phone_text(message: Message, state: FSMContext) -> None:
    phone = message.text.strip().replace(" ", "")
    if not phone.startswith("+"):
        phone = "+998" + phone.lstrip("0")

    if len(phone) < 12:
        await message.answer("❌ Noto'g'ri raqam. Qayta kiriting: <code>+998901234567</code>")
        return

    await _send_sms(message, state, phone)


async def _send_sms(message: Message, state: FSMContext, phone: str) -> None:
    """SMS yuborish va keyingi state'ga o'tish."""
    try:
        async with get_api_client() as api:
            await api.send_sms(phone)
    except ArosAPIError as e:
        await message.answer(f"❌ Xatolik: {e}")
        return

    await state.update_data(phone=phone)
    await state.set_state(LoginState.waiting_code)
    await message.answer(
        f"📨 <b>{phone}</b> raqamiga SMS kod yuborildi.\n"
        "Kodni kiriting:",
        reply_markup=ReplyKeyboardRemove(),
    )


# ─── SMS kod qabul qilish ────────────────────────────────────────────────────

@router.message(LoginState.waiting_code, F.text)
async def handle_sms_code(message: Message, state: FSMContext) -> None:
    code = message.text.strip()
    data = await state.get_data()
    phone = data.get("phone", "")

    try:
        async with get_api_client() as api:
            token = await api.verify_sms(phone, code)
    except ArosAPIError as e:
        await message.answer(f"❌ {e}\nQayta urinib ko'ring:")
        return

    # Tokenni state'ga saqlaymiz — barcha keyingi so'rovlarda ishlatiladi
    await state.update_data(token=token)
    await state.set_state(None)

    # Profil ma'lumotlarini olamiz
    try:
        async with get_api_client(token=token) as api:
            profile = await api.get_profile()
        await message.answer(
            f"✅ Xush kelibsiz, <b>{profile.first_name}</b>!\n\n"
            f"👤 {profile.first_name} {profile.last_name}\n"
            f"📱 {profile.phone}\n"
            f"💰 Keshbek: <b>{format_price(profile.cashback_balance)}</b>\n"
            f"🏪 Ombor: <b>{profile.warehouse_name}</b>"
        )
    except ArosAPIError:
        await message.answer("✅ Muvaffaqiyatli kirdingiz!")


# ─── /profile buyrug'i ───────────────────────────────────────────────────────

@router.message(Command("profile"))
async def cmd_profile(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    token = data.get("token")

    if not token:
        await message.answer("❌ Tizimga kirmagansiz. /login")
        return

    try:
        async with get_api_client(token=token) as api:
            profile = await api.get_profile()
    except ArosAPIError as e:
        await message.answer(f"❌ {e}")
        return

    await message.answer(
        f"👤 <b>Profil</b>\n\n"
        f"Ism: {profile.first_name} {profile.last_name}\n"
        f"Telefon: {profile.phone}\n"
        f"💰 Keshbek: <b>{format_price(profile.cashback_balance)}</b>\n"
        f"🏪 Ombor: <b>{profile.warehouse_name}</b>"
    )


# ─── /logout buyrug'i ────────────────────────────────────────────────────────

@router.message(Command("logout"))
async def cmd_logout(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("👋 Tizimdan chiqdingiz.")
