"""
Ma'lumot modellari (Data Models).
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ProductImage:
    url: str


@dataclass
class Product:
    id: str | int
    title: str
    price: float
    old_price: Optional[float]
    images: list[ProductImage] = field(default_factory=list)
    url: Optional[str] = None

    @property
    def has_discount(self) -> bool:
        return self.old_price is not None and self.old_price > self.price

    @property
    def discount_percent(self) -> int:
        if not self.has_discount:
            return 0
        return int((1 - self.price / self.old_price) * 100)

    @property
    def main_image_url(self) -> Optional[str]:
        return self.images[0].url if self.images else None


@dataclass
class UserProfile:
    """Foydalanuvchi profili."""
    id: int
    phone: str
    first_name: str
    last_name: str
    cashback_balance: float
    warehouse_name: str     # Biriktirilgan ombor nomi
    role: str


@dataclass
class CartItem:
    """Savat elementi."""
    product_variant_id: int
    title: str
    price: float
    quantity: int
    image_url: Optional[str] = None

    @property
    def total_price(self) -> float:
        return self.price * self.quantity
