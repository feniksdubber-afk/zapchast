"""
Yordamchi funksiyalar (Utilities).
Narx formatlash, matn tayyorlash va boshqa umumiy operatsiyalar.
"""

from models import Product


def format_price(amount: float) -> str:
    """
    Narxni foydalanuvchiga qulay ko'rinishga keltiradi.

    Misol:
        185000  → "185 000 so'm"
        1250000 → "1 250 000 so'm"
        99.5    → "99 so'm"  (tiyinlar uchun yaxlitlash)
    """
    # Butun songa yaxlitlash (tiyin yo'q bo'lsa)
    rounded = int(amount) if amount == int(amount) else amount
    formatted = f"{rounded:,}".replace(",", " ")
    return f"{formatted} so'm"


def build_product_caption(product: Product) -> str:
    """
    Mahsulot uchun Telegram xabari matnini (caption) tayyorlaydi.
    HTML parse_mode ishlatiladi.

    Misol chiqishi:
        📦 Samsung Galaxy A55
        💰 Narx: 4 299 000 so'm
        🏷 Eski narx: ~~5 000 000 so'm~~ (-14%)
        🔗 Ko'rish
    """
    lines = [f"📦 <b>{product.title}</b>", ""]

    # Narx bloki
    lines.append(f"💰 <b>Narx:</b> {format_price(product.price)}")

    if product.has_discount and product.old_price:
        lines.append(
            f"🏷 <s>{format_price(product.old_price)}</s>  "
            f"<b>-{product.discount_percent}%</b>"
        )

    # Mahsulot havolasi
    if product.url:
        lines.append("")
        lines.append(f'🔗 <a href="{product.url}">Saytda ko\'rish</a>')

    return "\n".join(lines)


def build_product_button_label(product: Product) -> str:
    """
    Inline tugma uchun qisqa yorliq matnini tayyorlaydi.
    Telegram tugma matn uzunligi cheklangani uchun qisqa saqlanadi.

    Misol: "Samsung A55 — 4 299 000 so'm"
    """
    # Nom 30 belgidan uzun bo'lsa, qirqib qo'yamiz
    short_title = product.title[:30] + "…" if len(product.title) > 30 else product.title
    return f"{short_title} — {format_price(product.price)}"
