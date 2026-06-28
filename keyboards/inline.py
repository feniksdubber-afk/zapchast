"""
Telegram Inline klaviaturalar (Keyboards).
Mahsulot ro'yxati va navigatsiya uchun tugmalar yaratadi.
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from models import Product
from utils.formatting import build_product_button_label


def build_product_list_keyboard(products: list[Product]) -> InlineKeyboardMarkup:
    """
    Qidiruv natijalari uchun Inline klaviatura yaratadi.
    Har bir tugmada mahsulot nomi va narxi ko'rsatiladi.
    Tugmani bosish mahsulotning batafsil ko'rinishini chiqaradi.

    Tugma callback_data formati: "product:{id}"
    """
    builder = InlineKeyboardBuilder()

    for product in products:
        label = build_product_button_label(product)
        builder.button(
            text=label,
            callback_data=f"product:{product.id}",
        )

    # Har bir tugmani alohida qatorga joylashtirish
    builder.adjust(1)
    return builder.as_markup()


def build_product_detail_keyboard(product: Product) -> InlineKeyboardMarkup:
    """
    Mahsulot detail ko'rinishi uchun tugmalar.
    O'xshash mahsulotlar va saytga havola tugmalari.
    """
    builder = InlineKeyboardBuilder()

    # O'xshash mahsulotlar tugmasi
    builder.button(
        text="🔍 O'xshash mahsulotlar",
        callback_data=f"similar:{product.id}",
    )

    # Saytda ko'rish (agar URL mavjud bo'lsa)
    if product.url:
        builder.button(
            text="🌐 Saytda ko'rish",
            url=product.url,
        )

    # Orqaga qaytish tugmasi
    builder.button(
        text="◀️ Orqaga",
        callback_data="back_to_search",
    )

    builder.adjust(1)
    return builder.as_markup()


def build_similar_keyboard(product_id: str | int) -> InlineKeyboardMarkup:
    """
    O'xshash mahsulotlar ko'rinishi uchun navigatsiya tugmasi.
    """
    builder = InlineKeyboardBuilder()
    builder.button(
        text="◀️ Orqaga",
        callback_data=f"product:{product_id}",
    )
    builder.adjust(1)
    return builder.as_markup()
