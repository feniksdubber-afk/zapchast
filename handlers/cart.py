"""
Savat handlerlari.
Ko'rish, qo'shish, o'chirish, miqdor o'zgartirish.
"""

import logging
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from models import CartItem
from services.api_client import ArosAPIError, get_api_client
from utils.formatting import format_price

logger = logging.getLogger(__name__)
router = Router(name="cart")


def _require_token(token: str | None) -> bool:
    return bool(token)


def _build_cart_keyboard(items: list[CartItem]):
    """Savat uchun inline klaviatura — har bir mahsulot uchun +/- va o'chirish."""
    builder = InlineKeyboardBuilder()
    for item in items:
        vid = item.product_variant_id
        # Mahsulot nomi (qisqa)
        short = item.title[:25] + "…" if len(item.title) > 25 else item.title
        builder.button(text=f"📦 {short}", callback_data=f"cart_info:{vid}")
        builder.button(text="➖", callback_data=f"cart_dec:{vid}")
        builder.button(text=f"{item.quantity} ta", callback_data=f"cart_qty:{vid}")
        builder.button(text="➕", callback_data=f"cart_inc:{vid}")
        builder.button(text="🗑", callback_data=f"cart_del:{vid}")
        builder.adjust(1, 4)  # birinchi qator: nom, ikkinchi: tugmalar

    builder.button(text="🔄 Yangilash", callback_data="cart_refresh")
    builder.adjust(1, 4, 1)
    return builder.as_markup()


def _cart_text(items: list[CartItem]) -> str:
    """Savat matnini formatlaydi."""
    if not items:
        return "🛒 Savat bo'sh.\n\nMahsulot qidirish uchun nomini yozing."

    lines = ["🛒 <b>Savatingiz:</b>\n"]
    total = 0.0
    for i, item in enumerate(items, 1):
        lines.append(
            f"{i}. {item.title}\n"
            f"   {format_price(item.price)} × {item.quantity} = "
            f"<b>{format_price(item.total_price)}</b>"
        )
        total += item.total_price

    lines.append(f"\n💰 <b>Jami: {format_price(total)}</b>")
    lines.append("\n🌐 Buyurtma berish: aros.uz saytiga kiring")
    return "\n".join(lines)


# ─── /cart buyrug'i ──────────────────────────────────────────────────────────

@router.message(Command("cart"))
async def cmd_cart(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    token = data.get("token")

    if not token:
        await message.answer("❌ Avval tizimga kiring: /login")
        return

    try:
        async with get_api_client(token=token) as api:
            items = await api.get_cart()
    except ArosAPIError as e:
        await message.answer(f"❌ {e}")
        return

    await message.answer(
        _cart_text(items),
        reply_markup=_build_cart_keyboard(items) if items else None,
    )


# ─── Savatga qo'shish (mahsulot detail'dan) ──────────────────────────────────

@router.callback_query(F.data.startswith("add_to_cart:"))
async def handle_add_to_cart(callback: CallbackQuery, state: FSMContext) -> None:
    variant_id = int(callback.data.split(":")[1])

    data = await state.get_data()
    token = data.get("token")

    if not token:
        await callback.answer("❌ Avval /login orqali kiring!", show_alert=True)
        return

    try:
        async with get_api_client(token=token) as api:
            await api.add_to_cart(variant_id, quantity=1)
    except ArosAPIError as e:
        await callback.answer(f"❌ {e}", show_alert=True)
        return

    await callback.answer("✅ Savatga qo'shildi!", show_alert=False)


# ─── Miqdor oshirish ─────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("cart_inc:"))
async def handle_cart_inc(callback: CallbackQuery, state: FSMContext) -> None:
    variant_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    token = data.get("token")

    if not token:
        await callback.answer("❌ Login kerak!", show_alert=True)
        return

    try:
        async with get_api_client(token=token) as api:
            items = await api.get_cart()
            current = next((i for i in items if i.product_variant_id == variant_id), None)
            new_qty = (current.quantity + 1) if current else 1
            await api.add_to_cart(variant_id, quantity=new_qty)
            items = await api.get_cart()
    except ArosAPIError as e:
        await callback.answer(f"❌ {e}", show_alert=True)
        return

    await callback.answer("➕ Miqdor oshirildi")
    if callback.message:
        await callback.message.edit_text(
            _cart_text(items),
            reply_markup=_build_cart_keyboard(items),
        )


# ─── Miqdor kamaytirish ───────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("cart_dec:"))
async def handle_cart_dec(callback: CallbackQuery, state: FSMContext) -> None:
    variant_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    token = data.get("token")

    if not token:
        await callback.answer("❌ Login kerak!", show_alert=True)
        return

    try:
        async with get_api_client(token=token) as api:
            items = await api.get_cart()
            current = next((i for i in items if i.product_variant_id == variant_id), None)

            if current and current.quantity > 1:
                await api.add_to_cart(variant_id, quantity=current.quantity - 1)
            else:
                # 1 ta qolsa — o'chirib yuboramiz
                await api.remove_from_cart(variant_id)

            items = await api.get_cart()
    except ArosAPIError as e:
        await callback.answer(f"❌ {e}", show_alert=True)
        return

    await callback.answer("➖ Miqdor kamaytirildi")
    if callback.message:
        await callback.message.edit_text(
            _cart_text(items),
            reply_markup=_build_cart_keyboard(items) if items else None,
        )


# ─── O'chirish ───────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("cart_del:"))
async def handle_cart_del(callback: CallbackQuery, state: FSMContext) -> None:
    variant_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    token = data.get("token")

    if not token:
        await callback.answer("❌ Login kerak!", show_alert=True)
        return

    try:
        async with get_api_client(token=token) as api:
            await api.remove_from_cart(variant_id)
            items = await api.get_cart()
    except ArosAPIError as e:
        await callback.answer(f"❌ {e}", show_alert=True)
        return

    await callback.answer("🗑 O'chirildi")
    if callback.message:
        await callback.message.edit_text(
            _cart_text(items),
            reply_markup=_build_cart_keyboard(items) if items else None,
        )


# ─── Yangilash ───────────────────────────────────────────────────────────────

@router.callback_query(F.data == "cart_refresh")
async def handle_cart_refresh(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    token = data.get("token")

    if not token:
        await callback.answer("❌ Login kerak!", show_alert=True)
        return

    try:
        async with get_api_client(token=token) as api:
            items = await api.get_cart()
    except ArosAPIError as e:
        await callback.answer(f"❌ {e}", show_alert=True)
        return

    await callback.answer("🔄 Yangilandi")
    if callback.message:
        await callback.message.edit_text(
            _cart_text(items),
            reply_markup=_build_cart_keyboard(items) if items else None,
        )


# ─── cart_info (nom bosish — hech narsa qilmaymiz) ───────────────────────────

@router.callback_query(F.data.startswith("cart_info:") | F.data.startswith("cart_qty:"))
async def handle_cart_noop(callback: CallbackQuery) -> None:
    await callback.answer()
