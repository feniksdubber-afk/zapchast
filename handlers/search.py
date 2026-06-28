"""
Qidiruv va mahsulot ko'rish handlerlari.
Natijalar kategoriya bo'yicha guruhlanib ko'rsatiladi.
"""

import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from keyboards.inline import (
    build_group_list_keyboard,
    build_variant_list_keyboard,
    build_product_detail_keyboard,
)
from models import Product, ProductImage, WarehouseStock
from services.api_client import ArosAPIError, get_api_client
from services.grouping import group_products, ProductGroup
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
    return [
        {
            "id": str(p.id),
            "title": p.title,
            "price": p.price,
            "old_price": p.old_price,
            "images": [img.url for img in p.images],
            "url": p.url,
            "price_b2c": p.price_b2c,
            "warehouse_stocks": [
                {"name": w.name, "quantity": w.quantity} for w in p.warehouse_stocks
            ],
        }
        for p in products
    ]


def _dict_to_product(d: dict) -> Product:
    return Product(
        id=d["id"],
        title=d["title"],
        price=d["price"],
        old_price=d.get("old_price"),
        images=[ProductImage(url=u) for u in d.get("images", [])],
        url=d.get("url"),
        price_b2c=d.get("price_b2c"),
        warehouse_stocks=[
            WarehouseStock(name=w["name"], quantity=w["quantity"])
            for w in d.get("warehouse_stocks", [])
        ],
    )


async def _send_product(message: Message, product: Product, keyboard) -> None:
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

    # Guruhlash
    groups = group_products(products)

    await state.set_state(SearchState.results)
    await state.update_data(
        products=_products_to_dict(products),
        last_query=query,
    )

    # Agar faqat 1 ta guruh va 1 ta variant — to'g'ridan detail
    if len(groups) == 1 and groups[0].single:
        keyboard = build_product_detail_keyboard(groups[0].variants[0])
        await _send_product(message, groups[0].variants[0], keyboard)
        return

    keyboard = build_group_list_keyboard(groups)

    # Guruhlar soni va umumiy variantlar
    total_variants = sum(g.count for g in groups)
    group_count = len(groups)

    await message.answer(
        f"🔍 <b>'{query}'</b> — {total_variants} ta natija, {group_count} ta kategoriya:\n"
        "Kategoriyani tanlang 👇",
        reply_markup=keyboard,
    )


# ─── HANDLER 2: Kategoriya bosildi → variantlar ─────────────────────────────

@router.callback_query(F.data.startswith("group:"))
async def handle_group_select(callback: CallbackQuery, state: FSMContext) -> None:
    part_name = callback.data.split(":", 1)[1]
    await callback.answer()

    data = await state.get_data()
    saved_products = data.get("products", [])
    query = data.get("last_query", "")

    all_products = [_dict_to_product(p) for p in saved_products]

    # Shu kategoriyaga tegishli variantlarni topamiz
    groups = group_products(all_products)
    group = next((g for g in groups if g.part_name == part_name), None)

    if not group:
        await callback.message.answer("❌ Kategoriya topilmadi. Qayta qidiring.")
        return

    keyboard = build_variant_list_keyboard(group)
    await callback.message.answer(
        f"📦 <b>{part_name}</b> — {group.count} ta variant:\n"
        "Variantni tanlang 👇",
        reply_markup=keyboard,
    )


# ─── HANDLER 3: Variant/mahsulot detail ─────────────────────────────────────

@router.callback_query(F.data.startswith("product:"))
async def handle_product_detail(callback: CallbackQuery, state: FSMContext) -> None:
    product_id = callback.data.split(":", 1)[1]
    await callback.answer()

    if not callback.message:
        return

    data = await state.get_data()
    saved_products = data.get("products", [])

    product_dict = next(
        (p for p in saved_products if str(p["id"]) == str(product_id)),
        None
    )

    if not product_dict:
        await callback.message.answer("❌ Mahsulot topilmadi. Qayta qidiring.")
        return

    p = _dict_to_product(product_dict)
    keyboard = build_product_detail_keyboard(p)
    await _send_product(callback.message, p, keyboard)


# ─── HANDLER 4: Kategoriyalar ro'yxatiga qaytish ────────────────────────────

@router.callback_query(F.data == "back_to_groups")
async def handle_back_to_groups(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()

    data = await state.get_data()
    saved_products = data.get("products", [])
    query = data.get("last_query", "")

    if not saved_products:
        await callback.message.answer("🔍 Yangi qidiruv uchun mahsulot nomini yozing.")
        return

    all_products = [_dict_to_product(p) for p in saved_products]
    groups = group_products(all_products)
    keyboard = build_group_list_keyboard(groups)

    total_variants = sum(g.count for g in groups)
    await callback.message.answer(
        f"🔍 <b>'{query}'</b> — {total_variants} ta natija:\n"
        "Kategoriyani tanlang 👇",
        reply_markup=keyboard,
    )


# ─── HANDLER 5: O'xshash mahsulotlar ────────────────────────────────────────

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

    groups = group_products(similar_products)

    await state.update_data(
        products=_products_to_dict(similar_products),
        last_query="o'xshash mahsulotlar",
    )

    keyboard = build_group_list_keyboard(groups)
    total = sum(g.count for g in groups)
    await callback.message.answer(
        f"🔗 <b>{total}</b> ta o'xshash mahsulot:",
        reply_markup=keyboard,
    )
