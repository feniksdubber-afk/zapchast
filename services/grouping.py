"""
Qidiruv natijalarini kategoriya bo'yicha guruhlash.

Samsung A12 uchun misol:
  Ekran (2 ta)  →  [LCD], [OLED big]
  Krişka (3 ta) →  [Qora], [Oq], [Ko'k]
  Batareya (1 ta) → to'g'ridan detail
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataclasses import dataclass, field
from models import Product


@dataclass
class ProductGroup:
    """Bir kategoriya ichidagi variantlar to'plami."""
    part_name: str          # "Ekran", "Krişka", "Batareya" ...
    variants: list[Product] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.variants)

    @property
    def single(self) -> bool:
        """Faqat 1 ta variant — to'g'ridan detail."""
        return len(self.variants) == 1


def _extract_part_name(product: Product) -> str:
    """
    Mahsulot nomidan kategoriya qismini ajratib oladi.
    "Samsung A12 — Ekran (LCD)" → "Ekran"
    "Samsung A12 — Krişka"     → "Krişka"
    "Samsung A12"              → "Umumiy"
    """
    title = product.title
    if " — " in title:
        # "Model — Kategoriya (Sifat)" → "Kategoriya"
        part = title.split(" — ", 1)[1]
        # "(Sifat)" qismini olib tashlaymiz
        if "(" in part:
            part = part[:part.index("(")].strip()
        return part.strip()
    return "Umumiy"


def _variant_label(product: Product) -> str:
    """
    Variant tugmasi uchun qisqa yorliq.
    "Samsung A12 — Ekran (LCD)" → "LCD"
    "Samsung A12 — Krişka (Qora rang)" → "Qora rang"
    "Samsung A12 — Ekran" → narx ko'rsatiladi
    """
    title = product.title
    if "(" in title and title.endswith(")"):
        return title[title.rindex("(") + 1:-1].strip()
    # Qavslar yo'q — narxni label sifatida ishlatamiz
    from utils.formatting import format_price
    return format_price(product.price)


def group_products(products: list[Product]) -> list[ProductGroup]:
    """
    Mahsulotlar ro'yxatini kategoriya bo'yicha guruhlaydi.
    Tartib: birinchi uchragan tartibida saqlanadi.
    """
    order: list[str] = []
    groups: dict[str, ProductGroup] = {}

    for product in products:
        part = _extract_part_name(product)
        if part not in groups:
            groups[part] = ProductGroup(part_name=part)
            order.append(part)
        groups[part].variants.append(product)

    return [groups[k] for k in order]
