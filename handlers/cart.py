"""
Savat handlerlari + to'liq Checkout flow.

Flow:
  /cart
    → [✅ Buyurtma berish]
        → 1. To'lov usuli tanlash
        → 2. Yetkazib berish usuli tanlash (uy / olib ketish)
        → 3. Manzil tanlash (API dan)
        → 4. Xulosa + tasdiqlash
        → 5. create-orders/ → ✅
"""

import asyncio
import logging
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collections import defaultdict

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder

from models import CartItem
from services.api_client import ArosAPIError, get_api_client
from utils.formatting import format_price

logger = logging.getLogger(__name__)
router = Router(name="cart")

_cart_locks: dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)


# ─── FSM ─────────────────────────────────────────────────────────────────────

class CheckoutState(StatesGroup):
    payment     = State()   # To'lov usuli tanlanmoqda
    delivery    = State()   # Yetkazib berish usuli tanlanmoqda
    address     = State()   # Manzil tanlanmoqda
    confirm     = State()   # Tasdiqlash kutilmoqda


# ─── Klaviaturalar ───────────────────────────────────────────────────────────

def _build_cart_keyboard(items: list[CartItem]):
    builder = InlineKeyboardBuilder()
    for item in items:
        vid = item.product_variant_id
        short = item.title[:25] + "…" if len(item.title) > 25 else item.title
        builder.button(text=f"📦 {short}", callback_data=f"cart_info:{vid}")
        builder.button(text="➖", callback_data=f"cart_dec:{vid}")
        builder.button(text=f"{item.quantity} ta", callback_data=f"cart_qty:{vid}")
        builder.button(text="➕", callback_data=f"cart_inc:{vid}")
        builder.button(text="🗑", callback_data=f"cart_del:{vid}")
        builder.adjust(1, 4)

    builder.button(text="✅ Buyurtma berish", callback_data="checkout_start")
    builder.button(text="🔄 Yangilash", callback_data="cart_refresh")
    builder.adjust(1, 4, 1, 1)
    return builder.as_markup()


def _back_kb(callback_data: str, label: str = "◀️ Orqaga") -> object:
    b = InlineKeyboardBuilder()
    b.button(text=label, callback_data=callback_data)
    b.button(text="❌ Checkoutni bekor qilish", callback_data="checkout_cancel")
    b.adjust(1)
    return b.as_markup()


# ─── Matn formatlash ─────────────────────────────────────────────────────────

def _cart_text(items: list[CartItem]) -> str:
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
    return "\n".join(lines)


def _checkout_summary(data: dict) -> str:
    items_raw = data.get("checkout_items", [])
    total = sum(it["price"] * it["quantity"] for it in items_raw)
    payment_name  = data.get("checkout_payment_name", "—")
    delivery_name = data.get("checkout_delivery_name", "—")
    address_name  = data.get("checkout_address_name", "—")

    lines = [
        "📋 <b>Buyurtma xulosasi</b>\n",
        *[
            f"{i}. {it['title']}\n"
            f"   {it['quantity']} ta × {format_price(it['price'])} = "
            f"<b>{format_price(it['price'] * it['quantity'])}</b>"
            for i, it in enumerate(items_raw, 1)
        ],
        f"\n💰 <b>Jami: {format_price(total)}</b>",
        f"💳 <b>To'lov:</b> {payment_name}",
        f"🚚 <b>Yetkazish:</b> {delivery_name}",
        f"📍 <b>Manzil:</b> {address_name}",
        "\nBuyurtmani tasdiqlaysizmi?",
    ]
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# SAVAT — asosiy CRUD
# ═══════════════════════════════════════════════════════════════════════════

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
    await callback.answer("✅ Savatga qo'shildi!")


@router.callback_query(F.data.startswith("cart_inc:"))
async def handle_cart_inc(callback: CallbackQuery, state: FSMContext) -> None:
    variant_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    token = data.get("token")
    if not token:
        await callback.answer("❌ Login kerak!", show_alert=True)
        return
    lock = _cart_locks[callback.from_user.id]
    async with lock:
        try:
            async with get_api_client(token=token) as api:
                items = await api.get_cart()
                cur = next((i for i in items if i.product_variant_id == variant_id), None)
                await api.add_to_cart(variant_id, quantity=(cur.quantity + 1) if cur else 1)
                items = await api.get_cart()
        except ArosAPIError as e:
            await callback.answer(f"❌ {e}", show_alert=True)
            return
    await callback.answer("➕ Miqdor oshirildi")
    if callback.message:
        await callback.message.edit_text(_cart_text(items), reply_markup=_build_cart_keyboard(items))


@router.callback_query(F.data.startswith("cart_dec:"))
async def handle_cart_dec(callback: CallbackQuery, state: FSMContext) -> None:
    variant_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    token = data.get("token")
    if not token:
        await callback.answer("❌ Login kerak!", show_alert=True)
        return
    lock = _cart_locks[callback.from_user.id]
    async with lock:
        try:
            async with get_api_client(token=token) as api:
                items = await api.get_cart()
                cur = next((i for i in items if i.product_variant_id == variant_id), None)
                if cur and cur.quantity > 1:
                    await api.add_to_cart(variant_id, quantity=cur.quantity - 1)
                else:
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


@router.callback_query(F.data.startswith("cart_del:"))
async def handle_cart_del(callback: CallbackQuery, state: FSMContext) -> None:
    variant_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    token = data.get("token")
    if not token:
        await callback.answer("❌ Login kerak!", show_alert=True)
        return
    lock = _cart_locks[callback.from_user.id]
    async with lock:
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


@router.callback_query(F.data.startswith("cart_info:") | F.data.startswith("cart_qty:"))
async def handle_cart_noop(callback: CallbackQuery) -> None:
    await callback.answer()


# ═══════════════════════════════════════════════════════════════════════════
# CHECKOUT — 1-qadam: To'lov usuli
# ═══════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "checkout_start")
async def handle_checkout_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    data = await state.get_data()
    token = data.get("token")
    if not token:
        await callback.answer("❌ Login kerak!", show_alert=True)
        return

    msg = await callback.message.answer("⏳ Yuklanmoqda...")

    try:
        async with get_api_client(token=token) as api:
            items    = await api.get_cart()
            payments = await api.get_payment_methods()
    except ArosAPIError as e:
        await msg.delete()
        await callback.message.answer(f"❌ {e}")
        return

    if not items:
        await msg.delete()
        await callback.answer("🛒 Savat bo'sh!", show_alert=True)
        return

    # Savatni state'ga saqlaymiz
    await state.update_data(checkout_items=[
        {"id": it.product_variant_id, "title": it.title,
         "price": it.price, "quantity": it.quantity}
        for it in items
    ])
    await state.set_state(CheckoutState.payment)

    # To'lov usullari klaviaturasi
    builder = InlineKeyboardBuilder()
    for pm in payments:
        builder.button(
            text=f"💳 {pm.display_name}",
            callback_data=f"co_pay:{pm.id}:{pm.display_name[:30]}"
        )
    builder.button(text="❌ Bekor qilish", callback_data="checkout_cancel")
    builder.adjust(1)

    await msg.delete()
    await callback.message.answer(
        "💳 <b>To'lov usulini tanlang:</b>",
        reply_markup=builder.as_markup(),
    )


# ═══════════════════════════════════════════════════════════════════════════
# CHECKOUT — 2-qadam: Yetkazib berish usuli
# ═══════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("co_pay:"), CheckoutState.payment)
async def handle_checkout_payment(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    _, pay_id, pay_name = callback.data.split(":", 2)
    await state.update_data(
        checkout_payment_id=int(pay_id),
        checkout_payment_name=pay_name,
    )

    data = await state.get_data()
    token = data.get("token")
    await state.set_state(CheckoutState.delivery)

    msg = await callback.message.answer("⏳ Yuklanmoqda...")
    try:
        async with get_api_client(token=token) as api:
            enabled, disabled = await api.get_delivery_methods()
    except ArosAPIError as e:
        await msg.delete()
        await callback.message.answer(f"❌ {e}")
        return

    builder = InlineKeyboardBuilder()
    for dm in enabled:
        icon = "🏠" if dm.is_home_delivery else "🏪"
        label = "Uyga yetkazish" if dm.is_home_delivery else "Olib ketish"
        builder.button(
            text=f"{icon} {label}",
            callback_data=f"co_del:{dm.id}:{int(dm.is_home_delivery)}:{label[:20]}"
        )
    for dm in disabled:
        builder.button(
            text=f"🚫 (mavjud emas)",
            callback_data="co_del_disabled"
        )
    builder.button(text="◀️ Orqaga", callback_data="checkout_start")
    builder.button(text="❌ Bekor qilish", callback_data="checkout_cancel")
    builder.adjust(1)

    await msg.delete()
    await callback.message.answer(
        f"✅ To'lov: <b>{pay_name}</b>\n\n"
        "🚚 <b>Yetkazib berish usulini tanlang:</b>",
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data == "co_del_disabled")
async def handle_delivery_disabled(callback: CallbackQuery) -> None:
    await callback.answer("Bu usul hozir mavjud emas", show_alert=True)


# ═══════════════════════════════════════════════════════════════════════════
# CHECKOUT — 3-qadam: Manzil tanlash
# ═══════════════════════════════════════════════════════════════════════════

# Default region (Toshkent = 1, Farg'ona = 58 — API dan kelganiga qarab)
DEFAULT_REGION = 58

@router.callback_query(F.data.startswith("co_del:"), CheckoutState.delivery)
async def handle_checkout_delivery(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    _, del_id, is_home, del_name = callback.data.split(":", 3)
    await state.update_data(
        checkout_delivery_id=int(del_id),
        checkout_delivery_name=del_name,
        checkout_is_home_delivery=bool(int(is_home)),
    )
    await state.set_state(CheckoutState.address)

    data = await state.get_data()
    token = data.get("token")

    msg = await callback.message.answer("⏳ Manzillar yuklanmoqda...")
    try:
        async with get_api_client(token=token) as api:
            addresses = await api.get_order_addresses(
                region=DEFAULT_REGION,
                delivery_method=int(del_id),
            )
    except ArosAPIError as e:
        await msg.delete()
        await callback.message.answer(f"❌ {e}")
        return

    builder = InlineKeyboardBuilder()
    for addr in addresses:
        label = f"📍 {addr.name} — {addr.street}, {addr.building_number}"
        builder.button(
            text=label[:64],
            callback_data=f"co_addr:{addr.id}:{addr.name[:25]}"
        )
    builder.button(text="◀️ Orqaga", callback_data=f"co_pay:{data['checkout_payment_id']}:{data['checkout_payment_name']}")
    builder.button(text="❌ Bekor qilish", callback_data="checkout_cancel")
    builder.adjust(1)

    await msg.delete()
    await callback.message.answer(
        f"✅ Yetkazish: <b>{del_name}</b>\n\n"
        "📍 <b>Manzilni tanlang:</b>",
        reply_markup=builder.as_markup(),
    )


# ═══════════════════════════════════════════════════════════════════════════
# CHECKOUT — 4-qadam: Xulosa va tasdiqlash
# ═══════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("co_addr:"), CheckoutState.address)
async def handle_checkout_address(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    _, addr_id, addr_name = callback.data.split(":", 2)
    await state.update_data(
        checkout_address_id=int(addr_id),
        checkout_address_name=addr_name,
    )
    await state.set_state(CheckoutState.confirm)

    data = await state.get_data()

    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Tasdiqlash", callback_data="checkout_confirm")
    builder.button(text="◀️ Orqaga", callback_data=f"co_del:{data['checkout_delivery_id']}:{int(data['checkout_is_home_delivery'])}:{data['checkout_delivery_name']}")
    builder.button(text="❌ Bekor qilish", callback_data="checkout_cancel")
    builder.adjust(1)

    await callback.message.answer(
        _checkout_summary(data),
        reply_markup=builder.as_markup(),
    )


# ═══════════════════════════════════════════════════════════════════════════
# CHECKOUT — 5-qadam: Buyurtma yuborish
# ═══════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "checkout_confirm", CheckoutState.confirm)
async def handle_checkout_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    data = await state.get_data()
    token = data.get("token")
    if not token:
        await callback.answer("❌ Login kerak!", show_alert=True)
        return

    msg = await callback.message.answer("⏳ Buyurtma yuborilmoqda...")

    payload = {
        "payment_method": data.get("checkout_payment_id"),
        "delivery_method": data.get("checkout_delivery_id"),
        "address":         data.get("checkout_address_id"),
    }

    try:
        async with get_api_client(token=token) as api:
            result_msg = await api.create_order(payload)
    except ArosAPIError as e:
        await msg.delete()
        await callback.message.answer(f"❌ Xatolik: {e}")
        await state.set_state(None)
        return

    await msg.delete()

    # State tozalash
    await state.set_state(None)
    await state.update_data(
        checkout_items=None, checkout_payment_id=None,
        checkout_payment_name=None, checkout_delivery_id=None,
        checkout_delivery_name=None, checkout_address_id=None,
        checkout_address_name=None, checkout_is_home_delivery=None,
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="🛒 Savatni ko'rish", callback_data="cart_refresh")
    builder.adjust(1)

    await callback.message.answer(
        f"✅ <b>{result_msg or 'Buyurtma muvaffaqiyatli berildi!'}</b>\n\n"
        f"💳 To'lov: {data.get('checkout_payment_name')}\n"
        f"🚚 Yetkazish: {data.get('checkout_delivery_name')}\n"
        f"📍 Manzil: {data.get('checkout_address_name')}\n\n"
        "Tez orada operatorimiz siz bilan bog'lanadi.",
        reply_markup=builder.as_markup(),
    )


# ═══════════════════════════════════════════════════════════════════════════
# CHECKOUT — Bekor qilish (istalgan vaqtda)
# ═══════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "checkout_cancel")
async def handle_checkout_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer("❌ Bekor qilindi")
    await state.set_state(None)
    await state.update_data(
        checkout_items=None, checkout_payment_id=None,
        checkout_payment_name=None, checkout_delivery_id=None,
        checkout_delivery_name=None, checkout_address_id=None,
        checkout_address_name=None, checkout_is_home_delivery=None,
    )
    if callback.message:
        await callback.message.answer(
            "❌ Buyurtma bekor qilindi.\n\nSavatni ko'rish: /cart"
        )
