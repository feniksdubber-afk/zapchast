"""
JSON Parser Xizmati.
"""

import logging, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Any
from models import Product, ProductImage

logger = logging.getLogger(__name__)


def _parse_image(raw: Any) -> ProductImage | None:
    if isinstance(raw, str):
        return ProductImage(url=raw)
    if not isinstance(raw, dict):
        return None
    url = raw.get("image") or raw.get("url") or raw.get("original") or raw.get("src")
    return ProductImage(url=url) if url else None


def _parse_price(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def parse_product(raw: dict) -> Product | None:
    title = (raw.get("title") or raw.get("name") or raw.get("product_name") or "").strip()
    if not title:
        return None

    price = _parse_price(raw.get("selling_price") or raw.get("price") or raw.get("current_price"))
    if price is None:
        return None

    old_price = _parse_price(raw.get("old_price") or raw.get("original_price") or raw.get("compare_price"))

    raw_images = raw.get("images") or raw.get("photos") or []
    images = [img for raw_img in raw_images if (img := _parse_image(raw_img))]

    product_id = raw.get("id") or raw.get("variant_id") or raw.get("pk") or ""
    product_url = raw.get("url") or raw.get("link") or raw.get("absolute_url")

    return Product(id=product_id, title=title, price=price, old_price=old_price, images=images, url=product_url)


def parse_search_results(data: dict) -> list[Product]:
    items: list = data.get("results") or data.get("data") or data.get("items") or (data if isinstance(data, list) else [])
    return [p for raw in items if isinstance(raw, dict) and (p := parse_product(raw))]


def parse_similar_products(data: dict | list) -> list[Product]:
    items = data if isinstance(data, list) else (data.get("results") or data.get("data") or [])
    return [p for raw in items if isinstance(raw, dict) and (p := parse_product(raw))]
