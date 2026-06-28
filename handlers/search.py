"""
Qidiruv va mahsulot ko'rish handlerlari.
Foydalanuvchi qidiruvdan batafsil ko'rinishgacha bo'lgan barcha holatlarni boshqaradi.
"""

import logging

from aiogram import F, Router
from aiogram.types import (
    CallbackQuery,
    InputMediaPhoto,
    Message,
)

from keyboards.inline import (
    build_product_detail_keyboard,
    build_product_list_keyboard,
    build_similar_keyboard,
)
from models import Product
from services.api_client import ArosAPIError, get_api_client
from utils.formatting import build_product_caption

logger = logging.getLogger(__name__)
router = Router(name="search")

# Xato xabarlari — foydalanuvchiga tushunarli tilda
ERROR_MESSAGES = {
    404: "😕 Mahsulot topilmadi.",
    500: "⚠️ Server muammosi yuz berdi. Keyinroq urinib ko'ring.",
    "timeout": "⏳ So'rov vaqti tugadi. Internet aloqangizni tekshiring.",
    "connect": "📡 Internetga ulanib bo'lmadi. Aloqangizni tekshiring.",
    "default": "❌ Xatolik yuz berdi. Keyinroq urinib ko'ring.",
}


def _get_error_text(error: ArosAPIError) -> str:
    """Xatolik kodiga qarab foydalanuvchiga mos xabar tanlaydi."""
    if error.status_code:
        return ERROR_MESSAGES.get(error.status_code, ERROR_MESSAGES["default"])
    msg = str(error).lower()
    if "vaqti" in msg or "timeout" in msg:
        return ERROR_MESSAGES["timeout"]
    if "ulanib" in msg or "connect" in msg:
        return ERROR_MESSAGES["connect"]
    return ERROR_MESSAGES["default"]


async def _send_product_photo(
    message: Message,
    product: Product,
    keyboard,
) -> None:
    """
    Mahsulotni rasm yoki matn xabari sifatida yuboradi.
    Agar rasm yo'q bo'lsa, oddiy matn xabari yuboriladi.
    """
    caption = build_product_caption(product)

    if product.main_image_url:
        try:
            await message.answer_photo(
                photo=product.main_image_url,
                caption=caption,
                reply_markup=keyboard,
            )
            return
        except Exception:
            # Rasm yuklashda xatolik — matn xabariga o'tish
            logger.warning("Rasm yuklashda xatolik: %s", product.main_image_url)

    # Rasmiz matn xabari
    await message.answer(caption, reply_markup=keyboard)


# ─────────────────────────────────────────────
# HANDLER 1: Matnli qidiruv
# ─────────────────────────────────────────────

@router.message(F.text & ~F.text.startswith("/"))
async def handle_search(message: Message) -> None:
    """
    Foydalanuvchi yozgan har qanday matnni qidiruv so'rovi sifatida qabul qiladi.
    """
    query = message.text.strip()

    if len(query) < 2:
        await message.answer("✏️ Kamida 2 ta harf kiriting.")
        return

    # Yuklanayotganlik haqida xabar
    loading_msg = await message.answer("🔍 Qidirilmoqda...")

    try:
        async with get_api_client() as api:
            products = await api.search(query)
    except ArosAPIError as e:
        await loading_msg.delete()
        await message.answer(_get_error_text(e))
        return

    await loading_msg.delete()

    if not products:
        await message.answer(
            f"😕 <b>'{query}'</b> bo'yicha hech narsa topilmadi.\n"
            "Boshqa kalit so'z bilan urinib ko'ring."
        )
        return

    # Natijalar ro'yxatini Inline tugmalar bilan ko'rsatish
    keyboard = build_product_list_keyboard(products)
    await message.answer(
        f"✅ <b>'{query}'</b> bo'yicha <b>{len(products)}</b> ta natija topildi:\n"
        "Mahsulotni tanlang 👇",
        reply_markup=keyboard,
    )


# ─────────────────────────────────────────────
# HANDLER 2: Mahsulot detail ko'rinishi
# ─────────────────────────────────────────────

@router.callback_query(F.data.startswith("product:"))
async def handle_product_detail(callback: CallbackQuery) -> None:
    """
    Foydalanuvchi ro'yxatdan mahsulotni tanlaganda batafsil ma'lumot ko'rsatadi.
    """
    product_id = callback.data.split(":", 1)[1]

    await callback.answer()  # Telegram'ga "ishlov berildi" signali

    # O'xshash mahsulotlar orqali product ma'lumotini olish
    # (yoki alohida detail endpoint bo'lsa undan foydalanish)
    try:
        async with get_api_client() as api:
            similar = await api.get_similar(product_id)
    except ArosAPIError as e:
        logger.error("Similar API xatoligi: %s", e)
        similar = []

    # Callback xabari mavjudligini tekshirish
    if not callback.message:
        return

    keyboard = build_product_detail_keyboard(
        Product(id=product_id, title="", price=0, old_price=None)
    )

    if similar:
        # Birinchi o'xshash mahsulotdan foydalanib asosiy ma'lumotni ko'rsatish
        main = similar[0]
        keyboard = build_product_detail_keyboard(main)
        await _send_product_photo(callback.message, main, keyboard)
    else:
        await callback.message.answer(
            "ℹ️ Ushbu mahsulot haqida qo'shimcha ma'lumot topilmadi."
        )


# ─────────────────────────────────────────────
# HANDLER 3: O'xshash mahsulotlar
# ─────────────────────────────────────────────

@router.callback_query(F.data.startswith("similar:"))
async def handle_similar_products(callback: CallbackQuery) -> None:
    """
    Berilgan mahsulotga o'xshash mahsulotlarni ko'rsatadi.
    """
    product_id = callback.data.split(":", 1)[1]
    await callback.answer()

    if not callback.message:
        return

    loading_msg = await callback.message.answer("🔍 O'xshash mahsulotlar qidirilmoqda...")

    try:
        async with get_api_client() as api:
            similar_products = await api.get_similar(product_id)
    except ArosAPIError as e:
        await loading_msg.delete()
        await callback.message.answer(_get_error_text(e))
        return

    await loading_msg.delete()

    if not similar_products:
        await callback.message.answer("😕 O'xshash mahsulotlar topilmadi.")
        return

    keyboard = build_product_list_keyboard(similar_products)
    await callback.message.answer(
        f"🔗 <b>{len(similar_products)}</b> ta o'xshash mahsulot topildi:",
        reply_markup=keyboard,
    )


# ─────────────────────────────────────────────
# HANDLER 4: Orqaga qaytish
# ─────────────────────────────────────────────

@router.callback_query(F.data == "back_to_search")
async def handle_back(callback: CallbackQuery) -> None:
    """
    Foydalanuvchini qidiruv sahifasiga qaytaradi.
    """
    await callback.answer()
    if callback.message:
        await callback.message.answer(
            "🔍 Yangi qidiruv uchun mahsulot nomini yozing:"
        )
