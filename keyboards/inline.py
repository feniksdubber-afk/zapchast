"""
Telegram Inline klaviaturalar.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from models import Product
from utils.formatting import build_product_button_label, format_price
from services.grouping import ProductGroup, _variant_label


def build_group_list_keyboard(groups: list[ProductGroup]) -> InlineKeyboardMarkup:
    """Kategoriyalar ro'yxati — har biri tugma."""
    builder = InlineKeyboardBuilder()
    for group in groups:
        if group.single:
            # 1 ta variant → to'g'ridan product detail
            label = f"{group.part_name} — {format_price(group.variants[0].price)}"
            builder.button(text=label, callback_data=f"product:{group.variants[0].id}")
        else:
            # Ko'p variant → variant tanlash ekraniga
            label = f"{group.part_name} ({group.count} ta variant)"
            builder.button(text=label, callback_data=f"group:{group.part_name}")
    builder.adjust(1)
    return builder.as_markup()


def build_variant_list_keyboard(group: ProductGroup) -> InlineKeyboardMarkup:
    """Bir kategoriya ichidagi variantlar."""
    builder = InlineKeyboardBuilder()
    for variant in group.variants:
        label = f"{_variant_label(variant)} — {format_price(variant.price)}"
        builder.button(text=label, callback_data=f"product:{variant.id}")
    builder.button(text="◀️ Orqaga", callback_data="back_to_groups")
    builder.adjust(1)
    return builder.as_markup()


def build_product_list_keyboard(products: list[Product]) -> InlineKeyboardMarkup:
    """Oddiy mahsulot ro'yxati (guruhlash ishlatilmasa)."""
    builder = InlineKeyboardBuilder()
    for product in products:
        label = build_product_button_label(product)
        builder.button(text=label, callback_data=f"product:{product.id}")
    builder.adjust(1)
    return builder.as_markup()


def build_product_detail_keyboard(product: Product) -> InlineKeyboardMarkup:
    """Mahsulot detail — savatga qo'shish, o'xshashlar, orqaga."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🛒 Savatga qo'shish", callback_data=f"add_to_cart:{product.id}")
    builder.button(text="🔍 O'xshash mahsulotlar", callback_data=f"similar:{product.id}")
    if product.url:
        builder.button(text="🌐 Saytda ko'rish", url=product.url)
    builder.button(text="◀️ Orqaga", callback_data="back_to_groups")
    builder.adjust(1)
    return builder.as_markup()


def build_similar_keyboard(product_id: str | int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Orqaga", callback_data=f"product:{product_id}")
    builder.adjust(1)
    return builder.as_markup()
