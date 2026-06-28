"""
Qidiruv va mahsulot ko'rish handlerlari.
"""

import logging
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from keyboards.inline import build_product_list_keyboard, build_product_detail_keyboard
from models import Product
from services.api_client import ArosAPIError, get_api_client
from utils.formatting import build_product_caption

logger = logging.getLogger(__name__)
router = Router(name="search")

ERROR_MESSAGES = {
    404: "😕 Mahsulot topilmadi.",
    500: "⚠️ Server muammosi yuz berdi. Keyinroq urinib ko'ring.",
    "timeout": "⏳ So'rov vaqti tugadi. Internet aloqangizni tekshiring.",
    "connect": "📡 Internetga ulanib bo'lmadi. Aloqangizni tekshiring.",
    "default": "❌ Xatolik yuz berdi. Keyinroq urinib ko'ring.",
}


class SearchState(StatesGroup):
    """Qidiruv natijalari holatini saqlash uchun FSM."""
    results = State()


def _get_error_text(error: ArosAPIError) -> str:
    if error.status_code:
        return ERROR_MESSAGES.get(error.status_code, ERROR_MESSAGES["default"])
    msg = str(error).lower()
    if "vaqti" in msg or "timeout" in msg:
        return ERROR_MESSAGES["timeout"]
    if "ulanib" in msg or "connect" in msg:
        return ERROR_MESSAGES["connect"]
    return ERROR_MESSAGES["default"]


def _products_to_dict(products: list[Product]) -> list[dict]:
    """Product ro'yxatini JSON'ga saqlash uchun dict'ga aylantiradi."""
    return [
        {
            "id": str(p.id),
            "title": p.title,
            "price": p.price,
            "old_price": p.old_price,
            "images": [img.url for img in p.images],
            "url": p.url,
        }
        for p in products
    ]


def _dict_to_product(d: dict) -> Product:
    """Dict'dan Product modelini qayta tiklaydi."""
    from models import ProductImage
    return Product(
        id=d["id"],
        title=d["title"],
        price=d["price"],
        old_price=d.get("old_price"),
        images=[ProductImage(url=u) for u in d.get("images", [])],
        url=d.get("url"),
    )


async def _send_product(message: Message, product: Product, keyboard) -> None:
    """Mahsulotni rasm yoki matn sifatida yuboradi."""
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
            logger.warning("Rasm yuklashda xatolik: %s", product.main_image_url)
    await message.answer(caption, reply_markup=keyboard)


# ─── HANDLER 1: Matnli qidiruv ───────────────────────────────────────────────

@router.message(F.text & ~F.text.startswith("/"))
async def handle_search(message: Message, state: FSMContext) -> None:
    query = message.text.strip()
    if len(query) < 2:
        await message.answer("✏️ Kamida 2 ta harf kiriting.")
        return

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

    # Natijalarni FSM state'ga saqlaymiz — tugma bosilganda topib olinadi
    await state.set_state(SearchState.results)
    await state.update_data(products=_products_to_dict(products))

    keyboard = build_product_list_keyboard(products)
    await message.answer(
        f"✅ <b>'{query}'</b> bo'yicha <b>{len(products)}</b> ta natija topildi:\n"
        "Mahsulotni tanlang 👇",
        reply_markup=keyboard,
    )


# ─── HANDLER 2: Mahsulot detail ──────────────────────────────────────────────

@router.callback_query(F.data.startswith("product:"))
async def handle_product_detail(callback: CallbackQuery, state: FSMContext) -> None:
    product_id = callback.data.split(":", 1)[1]
    await callback.answer()

    if not callback.message:
        return

    # FSM'dan saqlangan natijalar ichidan ID bo'yicha topamiz
    data = await state.get_data()
    saved_products = data.get("products", [])

    product = next(
        (p for p in saved_products if str(p["id"]) == str(product_id)),
        None
    )

    if not product:
        await callback.message.answer("❌ Mahsulot ma'lumotlari topilmadi. Qayta qidiring.")
        return

    p = _dict_to_product(product)
    keyboard = build_product_detail_keyboard(p)
    await _send_product(callback.message, p, keyboard)


# ─── HANDLER 3: O'xshash mahsulotlar ─────────────────────────────────────────

@router.callback_query(F.data.startswith("similar:"))
async def handle_similar_products(callback: CallbackQuery, state: FSMContext) -> None:
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

    # O'xshash natijalarni ham state'ga saqlaymiz
    await state.update_data(products=_products_to_dict(similar_products))

    from keyboards.inline import build_product_list_keyboard
    keyboard = build_product_list_keyboard(similar_products)
    await callback.message.answer(
        f"🔗 <b>{len(similar_products)}</b> ta o'xshash mahsulot topildi:",
        reply_markup=keyboard,
    )


# ─── HANDLER 4: Orqaga ───────────────────────────────────────────────────────

@router.callback_query(F.data == "back_to_search")
async def handle_back(callback: CallbackQuery) -> None:
    await callback.answer()
    if callback.message:
        await callback.message.answer("🔍 Yangi qidiruv uchun mahsulot nomini yozing:")
