"""
Ma'lumot modellari (Data Models).
API'dan kelgan JSON ni tuzilgan Python obyektlariga aylantiradi.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ProductImage:
    """Mahsulot rasmi."""
    url: str


@dataclass
class Product:
    """
    Aros Market mahsuloti.
    API javobidagi barcha kerakli maydonlarni o'z ichiga oladi.
    """
    id: str | int
    title: str
    price: float                        # Joriy narx (so'm)
    old_price: Optional[float]          # Eski narx (chegirma bo'lsa)
    images: list[ProductImage] = field(default_factory=list)
    url: Optional[str] = None           # Mahsulot sahifasiga havola

    @property
    def has_discount(self) -> bool:
        """Chegirma mavjudligini tekshiradi."""
        return self.old_price is not None and self.old_price > self.price

    @property
    def discount_percent(self) -> int:
        """Chegirma foizini hisoblaydi."""
        if not self.has_discount:
            return 0
        return int((1 - self.price / self.old_price) * 100)

    @property
    def main_image_url(self) -> Optional[str]:
        """Birinchi (asosiy) rasmning URL'ini qaytaradi."""
        return self.images[0].url if self.images else None
