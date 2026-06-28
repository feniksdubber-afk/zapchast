"""
JSON Parser Xizmati.
"""

import logging, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Any
from models import Product, ProductImage, WarehouseStock

logger = logging.getLogger(__name__)


def _parse_warehouses(raw: dict) -> list[WarehouseStock]:
    """
    Mahsulotning har bir ombordagi miqdorini ajratib oladi.

    Aros API'da bu maydonning aniq nomi va shakli hali tasdiqlanmagan,
    shuning uchun bir nechta mumkin bo'lgan variantlar sinab ko'riladi.
    Agar hech biri mos kelmasa — bo'sh ro'yxat qaytadi va xom javob
    DEBUG logga yoziladi, shunda haqiqiy struktura Railway logidan
    ko'rib, shu funksiyani moslashtirish mumkin bo'ladi.
    """
    candidates = (
        raw.get("warehouses")
        or raw.get("warehouse_stocks")
        or raw.get("stocks")
        or raw.get("remains")
        or raw.get("warehouse_quantities")
        or raw.get("balances")
    )

    if not candidates or not isinstance(candidates, list):
        logger.debug(
            "Ombor ma'lumoti topilmadi. Mahsulot raw keys: %s | to'liq raw: %s",
            list(raw.keys()), raw,
        )
        return []

    result: list[WarehouseStock] = []
    for item in candidates:
        if not isinstance(item, dict):
            continue

        # Ombor nomi turlicha joylashgan bo'lishi mumkin:
        # {"name": "..."} yoki {"warehouse": {"name": "..."}} yoki {"warehouse": {"name_uz": "..."}}
        warehouse_obj = item.get("warehouse")
        if isinstance(warehouse_obj, dict):
            name = (
                warehouse_obj.get("name_uz")
                or warehouse_obj.get("name")
                or ""
            )
        else:
            name = (
                item.get("name_uz")
                or item.get("name")
                or item.get("warehouse_name")
                or (str(warehouse_obj) if warehouse_obj is not None else "")
            )

        quantity_raw = (
            item.get("quantity")
            if item.get("quantity") is not None
            else item.get("count")
            if item.get("count") is not None
            else item.get("remains")
            if item.get("remains") is not None
            else item.get("amount")
        )
        try:
            quantity = int(float(quantity_raw)) if quantity_raw is not None else 0
        except (ValueError, TypeError):
            quantity = 0

        if name:
            result.append(WarehouseStock(name=name, quantity=quantity))

    if not result:
        logger.debug(
            "Ombor ro'yxati topildi, lekin parse qilinmadi. raw candidates: %s",
            candidates,
        )

    return result


def _parse_image(raw: Any) -> ProductImage | None:
    if isinstance(raw, str):
        return ProductImage(url=raw)
    if not isinstance(raw, dict):
        return None
    # Aros API: images[].file — asl rasm, small_image_size/medium_image_size — kichraytirilgan versiyalar
    url = (
        raw.get("medium_image_size")
        or raw.get("file")
        or raw.get("image")
        or raw.get("url")
        or raw.get("original")
        or raw.get("src")
    )
    return ProductImage(url=url) if url else None


def _parse_price(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _build_title(raw: dict) -> str:
    """
    Telefon modeli + ehtiyot qism turi + sifat ko'rinishida nom yasaydi.
    Masalan: "Xiaomi 9T/9T Pro/K20/K20 Pro — Ekran (Oled big)"
    """
    base_name = (raw.get("name_uz") or raw.get("name") or "").strip()

    category = raw.get("category") or {}
    part_name = (category.get("name_uz") or category.get("name") or "").strip()

    # "Sifati" attributini attribute_values ichidan topamiz (rang emas)
    quality = None
    for attr_val in raw.get("attribute_values") or []:
        if not isinstance(attr_val, dict):
            continue
        attr = attr_val.get("attribute") or {}
        attr_name = (attr.get("name_uz") or attr.get("name") or "").lower()
        if "sifat" in attr_name or "quality" in attr_name:
            quality = attr_val.get("value_uz") or attr_val.get("value")
            break

    parts = [p for p in [base_name, part_name] if p]
    title = " — ".join(parts) if parts else base_name
    if quality:
        title += f" ({quality})"
    return title.strip(" —")


def parse_product(raw: dict) -> Product | None:
    title = _build_title(raw)
    if not title:
        return None

    base_price = _parse_price(raw.get("price"))
    if base_price is None:
        return None

    price_b2c = _parse_price(raw.get("price_b2c"))

    # discount mavjud bo'lsa — chegirmali narx asosiy, asl narx "eski narx" bo'lib ko'rsatiladi
    discount = raw.get("discount") or {}
    discount_price = _parse_price(discount.get("price")) if isinstance(discount, dict) else None

    if discount_price is not None and discount_price < base_price:
        price = discount_price
        old_price = base_price
    else:
        price = base_price
        old_price = None

    raw_images = raw.get("images") or raw.get("photos") or []
    images = [img for raw_img in raw_images if (img := _parse_image(raw_img))]

    product_id = raw.get("id") or raw.get("variant_id") or raw.get("pk") or ""
    product_url = raw.get("url") or raw.get("link") or raw.get("absolute_url")
    warehouse_stocks = _parse_warehouses(raw)

    return Product(
        id=product_id,
        title=title,
        price=price,
        old_price=old_price,
        images=images,
        url=product_url,
        price_b2c=price_b2c,
        warehouse_stocks=warehouse_stocks,
    )


def parse_search_results(data: dict | list) -> list[Product]:
    if isinstance(data, list):
        items = data
    else:
        items = data.get("results") or data.get("data") or data.get("items") or []
    return [p for raw in items if isinstance(raw, dict) and (p := parse_product(raw))]


def parse_similar_products(data: dict | list) -> list[Product]:
    items = data if isinstance(data, list) else (data.get("results") or data.get("data") or [])
    return [p for raw in items if isinstance(raw, dict) and (p := parse_product(raw))]
