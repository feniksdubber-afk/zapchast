"""
Telegram Inline klaviaturalar.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from models import Product
from utils.formatting import build_product_button_label


def build_product_list_keyboard(products: list[Product]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for product in products:
        label = build_product_button_label(product)
        builder.button(text=label, callback_data=f"product:{product.id}")
    builder.adjust(1)
    return builder.as_markup()


def build_product_detail_keyboard(product: Product) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔍 O'xshash mahsulotlar", callback_data=f"similar:{product.id}")
    if product.url:
        builder.button(text="🌐 Saytda ko'rish", url=product.url)
    builder.button(text="◀️ Orqaga", callback_data="back_to_search")
    builder.adjust(1)
    return builder.as_markup()


def build_similar_keyboard(product_id: str | int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Orqaga", callback_data=f"product:{product_id}")
    builder.adjust(1)
    return builder.as_markup()
