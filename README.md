# 🛒 Aros Market Telegram Bot

**aros.uz** mahsulotlarini Telegram orqali qidirish uchun bot.

## Loyiha tuzilmasi

```
aros_bot/
├── bot.py                  # Asosiy ishga tushirish fayli
├── config.py               # Konfiguratsiya (env o'zgaruvchilar)
├── models.py               # Ma'lumot modellari (Product, ProductImage)
│
├── services/
│   ├── api_client.py       # Aros API bilan HTTP muloqot
│   └── parser.py           # JSON → Python modellari
│
├── handlers/
│   ├── start.py            # /start, /help buyruqlari
│   └── search.py           # Qidiruv va mahsulot ko'rish
│
├── keyboards/
│   └── inline.py           # Inline tugmalar yaratish
│
├── utils/
│   └── formatting.py       # Narx va matn formatlash
│
├── requirements.txt
└── .env.example
```

## O'rnatish

```bash
# 1. Loyihani klonlash
git clone <repo_url>
cd aros_bot

# 2. Virtual muhit yaratish
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Kutubxonalarni o'rnatish
pip install -r requirements.txt

# 4. Muhit o'zgaruvchilarini sozlash
cp .env.example .env
# .env faylini tahrirlang va BOT_TOKEN qiymatini kiriting

# 5. Botni ishga tushirish
python bot.py
```

## Asosiy xususiyatlar

| Xususiyat | Tavsif |
|-----------|--------|
| 🔍 Qidiruv | Mahsulot nomini yozish yetarli |
| 📸 Rasmlar | Mahsulot rasmi va batafsil ma'lumot |
| 💰 Narx | Chegirmalar va eski narx ko'rsatiladi |
| 🔗 O'xshashlar | O'xshash mahsulotlar tavsiyasi |
| ⚡ Tezlik | Asinxron HTTP so'rovlar (httpx) |
| 🛡 Xatoliklar | Timeout, 404, 500 holatlar boshqariladi |
