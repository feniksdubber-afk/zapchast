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

    Aros API'da bu ro'yxat "variation_quantity" kaliti ostida keladi:
        "variation_quantity": [
            {"warehouse": {"name_uz": "Farg'ona", ...}, "quantity": 1,
             "available": true, "deliver_at": null, "days_after": null},
            ...
        ]
    """
    candidates = (
        raw.get("variation_quantity")
        or raw.get("warehouses")
        or raw.get("warehouse_stocks")
        or raw.get("stocks")
        or raw.get("remains")
        or raw.get("warehouse_quantities")
        or raw.get("balances")
    )

    if not candidates or not isinstance(candidates, list):
        logger.debug(
            "Ombor ma'lumoti topilmadi. Mahsulot raw keys: %s",
            list(raw.keys()),
        )
        return []

    result: list[WarehouseStock] = []
    for item in candidates:
        if not isinstance(item, dict):
            continue

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

        available = item.get("available", True)
        deliver_at = item.get("deliver_at")
        days_after = item.get("days_after")

        if name:
            result.append(WarehouseStock(
                name=name,
                quantity=quantity,
                available=bool(available),
                deliver_at=deliver_at,
                days_after=days_after,
            ))

    return result


def _parse_image(raw: Any) -> ProductImage | None:
    if isinstance(raw, str):
        return ProductImage(url=raw)
    if not isinstance(raw, dict):
        return None
    # Aros API: medium_image_size (500x500) yaxshi sifat uchun
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


_COLOR_NAMES = {
    "qora", "oq", "qizil", "ko'k", "kok", "yashil", "sariq", "kulrang",
    "kumush", "oltin", "pushti", "binafsha", "jigarrang", "to'q ko'k",
    "och ko'k", "moviy", "black", "white", "red", "blue", "green",
    "yellow", "gray", "grey", "silver", "gold", "pink", "purple", "brown",
}


def _extract_brand_from_raw(raw: dict) -> str:
    """
    Mahsulot raw data'sidan brand nomini ajratib oladi.

    Ikkita endpoint turli shaklda brand beradi:
      - cursor-search: product_models[0].brand.title
      - similar/category: manufacture_brand.title  YO  product_models[0].brand.title

    name_uz allaqachon brand nomini o'z ichiga olsa (masalan cursor-search
    da "Samsung Galaxy A12") — bo'sh qaytaramiz, takrorlanmasin.
    """
    # 1. product_models dan brand olish (cursor-search va similar ikkisida bor)
    pm = raw.get("product_models") or []
    if pm and isinstance(pm, list) and isinstance(pm[0], dict):
        brand_obj = pm[0].get("brand") or {}
        brand = brand_obj.get("title") or brand_obj.get("title_uz") or ""
        if brand:
            # name_uz allaqachon brand nomini o'z ichiga olganmi?
            name_uz = raw.get("name_uz") or raw.get("name") or ""
            if brand.lower() in name_uz.lower():
                return ""  # Takrorlanmasin
            return brand

    # 2. manufacture_brand (similar/category endpointda keladi)
    mb = raw.get("manufacture_brand") or {}
    if isinstance(mb, dict):
        brand = mb.get("title") or mb.get("title_uz") or ""
        if brand:
            name_uz = raw.get("name_uz") or raw.get("name") or ""
            if brand.lower() in name_uz.lower():
                return ""
            return brand

    return ""


def _build_title(raw: dict) -> str:
    """
    Mahsulot nomini quradi: Brand Model — Kategoriya (Sifat)

    Misol:
      cursor-search: "Samsung Galaxy A12 (A125) — Ekran (Original Frame)"
      similar:       "Tecno Spark Go 2023 — Ekran (Original)"
      NOVA V (brand yo'q): "NOVA V — Ekran (Original)"
    """
    base_name = (raw.get("name_uz") or raw.get("name") or "").strip()

    # Brand nomini oldindan qo'shamiz (agar name_uz da yo'q bo'lsa)
    brand = _extract_brand_from_raw(raw)
    if brand and base_name and not base_name.lower().startswith(brand.lower()):
        base_name = f"{brand} {base_name}"

    category = raw.get("category") or {}
    part_name = (category.get("name_uz") or category.get("name") or "").strip()

    # "Sifati" qiymatini attribute_values ichidan topamiz.
    # Ikkita format mavjud:
    #   1. cursor-search: {id, value_uz} — "attribute" kalit YO'Q
    #      → rang nomlariga mos kelmaydigan birinchi qiymat "sifat"
    #   2. similar/category: {id, value_uz, attribute: {name_uz: "Sifati"}}
    #      → "Sifati" nomli attribute aniq topiladi
    quality = None
    fallback_candidates: list[str] = []

    for attr_val in raw.get("attribute_values") or []:
        if not isinstance(attr_val, dict):
            continue
        attr = attr_val.get("attribute") or {}
        attr_name = (attr.get("name_uz") or attr.get("name") or "").lower()
        value = attr_val.get("value_uz") or attr_val.get("value")

        if "sifat" in attr_name or "quality" in attr_name:
            quality = value
            break

        is_color = bool(attr_val.get("color_hex")) or (
            value and value.strip().lower() in _COLOR_NAMES
        )
        if value and not is_color:
            fallback_candidates.append(value)

    if quality is None and fallback_candidates:
        quality = fallback_candidates[0]

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
    # link field bo'sh string bo'lishi mumkin — None ga tenglashtirish
    product_url = raw.get("url") or raw.get("link") or raw.get("absolute_url") or None
    if product_url == "":
        product_url = None

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
