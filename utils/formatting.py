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


def _format_delivery_note(product: Product) -> str | None:
    """
    Eng tezroq yetkazib bo'ladigan ombor asosida yetkazish vaqtini
    matn qilib qaytaradi. Agar 'available=True' ombor bo'lsa — hozir
    yetkazsa bo'ladi. Aks holda eng kichik days_after bo'yicha
    "Ertaga 16:00" kabi matn tuziladi.
    """
    stocks = [w for w in product.warehouse_stocks if w.quantity > 0]
    if not stocks:
        return None

    ready_now = next((w for w in stocks if w.available), None)
    if ready_now:
        return None  # Hozir mavjud — alohida eslatma kerak emas

    soonest = min(
        (w for w in stocks if w.days_after is not None),
        key=lambda w: w.days_after,
        default=None,
    )
    if not soonest:
        return None

    day_word = "Bugun" if soonest.days_after == 0 else (
        "Ertaga" if soonest.days_after == 1 else f"{soonest.days_after} kundan keyin"
    )
    time_part = f" {soonest.deliver_at[:5]}" if soonest.deliver_at else ""
    return f"⏰ Yetkazib berish vaqti: {day_word}{time_part}"


def build_product_caption(product: Product) -> str:
    """
    Mahsulot uchun Telegram xabari matnini (caption) tayyorlaydi.
    HTML parse_mode ishlatiladi.

    Misol chiqishi:
        📦 Xiaomi 9T — Ekran (Oled big)
        💰 Narx: 370 000 so'm
        🏷 Eski narx: ~~405 000 so'm~~ (-9%)
        🛍 Chakana narx: 420 000 so'm
        🏬 Omborda mavjud: 9 ta
           • Farg'ona: 0
           • Asosiy ombor: 9
        ⏰ Yetkazib berish vaqti: Ertaga 16:00
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

    if product.price_b2c is not None and product.price_b2c != product.price:
        lines.append(f"🛍 <b>Chakana narx:</b> {format_price(product.price_b2c)}")

    # Ombor bloki
    if product.warehouse_stocks:
        lines.append("")
        lines.append(f"🏬 <b>Omborda mavjud:</b> {product.total_stock} ta")
        for w in product.warehouse_stocks:
            lines.append(f"   • {w.name}: {w.quantity}")

        delivery_note = _format_delivery_note(product)
        if delivery_note:
            lines.append(delivery_note)

    # Mahsulot havolasi
    if product.url:
        lines.append("")
        lines.append(f'🔗 <a href="{product.url}">Saytda ko\'rish</a>')

    return "\n".join(lines)


def build_product_button_label(product: Product) -> str:
    """
    Inline tugma uchun qisqa yorliq matnini tayyorlaydi.
    Telegram tugma matn uzunligi cheklangani uchun qisqa saqlanadi.

    Misol: "Xiaomi 9T — Ekran (Oled big) — 370 000 so'm"
    """
    # Nom 35 belgidan uzun bo'lsa, qirqib qo'yamiz (narx ham qo'shilgani uchun)
    short_title = product.title[:35] + "…" if len(product.title) > 35 else product.title
    return f"{short_title} — {format_price(product.price)}"
