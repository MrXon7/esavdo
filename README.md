# 🛍 Telegram Savdo Do'koni Boti + Mini App (White-Label E-Commerce Platform)

Telegram bot va zamonaviy Telegram Mini App orqali ishlaydigan to'liq funksional onlayn savdo do'koni tizimi. 

Bu loyiha **White-Label** (oq-etiketka) shablon sifatida qurilgan — har bir mijoz o'zining mustaqil Telegram boti, Render veb-xizmati va Supabase PostgreSQL bazasi bilan o'rnatishi mumkin. Do'kon nomi, logotipi, tavsifi va aloqa ma'lumotlari kod ichida qattiq yozilmagan, balki admin panel orqali dinamik boshqariladi.

---

## 🚀 Texnologik Stack

- **Bot logikasi:** Python 3.10+ / [aiogram v3](https://docs.aiogram.dev/) (Webhook rejimida)
- **Backend API:** [FastAPI](https://fastapi.tiangolo.com/) + Uvicorn
- **Ma'lumotlar bazasi:** PostgreSQL / [Supabase](https://supabase.com/)
- **ORM:** [SQLAlchemy 2.0](https://www.sqlalchemy.org/) (asinxron, `asyncpg` drayveri bilan)
- **Frontend (Mini App):** Yengil Vanilla JavaScript, CSS3, [Telegram WebApp SDK](https://telegram.org/js/telegram-web-app.js)
- **Hosting:** [Render.com](https://render.com/) (Bepul Web Service tarifi uchun optimallashtirilgan)

---

## 🌟 Asosiy Xususiyatlar va Arxitektura

1. **Render Bepul Tarifi Uchun O'z-o'zini Uyg'otish (Self-Ping):**
   - Render bepul serverlari 15 daqiqa faollik bo'lmasa uyqu rejimiga o'tadi.
   - Loyihaning `main.py` ilovasida asinxron background task mavjud — u har 5 daqiqada o'zining `RENDER_EXTERNAL_URL/health` manziliga so'rov yuborib, tashqi xizmatlarsiz (UptimeRobot va h.k.) serverni doimo faol ushlab turadi.

2. **Telegram Rasm Saqlash Arxitekturasi (Zero-Disk Storage):**
   - Serverda doimiy disk talab qilinmaydi.
   - Admin botga rasm yoki albom (media-group) yuboradi → bot eng katta o'lchamdagi `file_id`ni `uploaded_images` jadvaliga `is_used=false` sifatida yozadi.
   - Admin Mini App'da yangi mahsulot qo'shayotganda galereyadan tayyor rasmlarni tanlaydi.
   - Rasmlar mijozlarga backenddagi `GET /images/{file_id}` xavfsiz keshlovchi proxy orqali uzatiladi (Bot tokeni frontendga aslo chiqmaydi).

3. **White-Label (Dinamik Brending):**
   - Do'kon nomi, logotipi, telefon raqami va valyutasi `store_settings` jadvalida saqlanadi.
   - Telegram botning `/start` xabarida, Mini App sarlavhasida va guruh e'lonlarida avtomatik yangilanadi.

4. **Buyurtmalar va Guruh Integratsiyasi:**
   - Yangi buyurtma tushganda admin guruhga xabar boradi (`ADMIN_GROUP_ID`).
   - Xabarda "✅ Tasdiqlash" va "❌ Rad etish" inline tugmalari mavjud.
   - Buyurtma holati o'zgarganda (tasdiqlandi, tayyorlanmoqda, yetkazilmoqda, yakunlandi) mijozning shaxsiy chatiga avtomatik bildirishnoma yuboriladi.
   - Mahsulotlarni bitta tugma bilan e'lonlar guruhiga (`PRODUCT_ANNOUNCE_GROUP_ID`) rasmi va narxi bilan chiqarish mumkin.

---

## 📁 Loyiha Strukturasi

```
ESavdo/
├── bot/
│   ├── bot_instance.py          # Aiogram Bot va Dispatcher
│   ├── handlers/
│   │   ├── start.py             # /start komandasi, dynamic branding, WebApp tugmasi
│   │   ├── admin_photo.py       # Admin yuborgan rasmlarni qabul qilib bazaga saqlash
│   │   └── admin_orders.py      # Guruhdagi inline tasdiqlash/bekor qilish callbacklari
│   └── services/
│       └── notifier.py          # Buyurtma xabarnomalari va guruhga e'lon xizmati
├── core/
│   ├── config.py                # Pydantic Settings, muhit o'zgaruvchilari
│   ├── database.py              # Async SQLAlchemy sessiyalari va dvigateli
│   └── security.py              # Telegram WebApp initData HMAC-SHA256 tekshiruvi
├── models/                      # SQLAlchemy modellari
│   ├── user.py                  # Foydalanuvchilar
│   ├── category.py              # Kategoriyalar
│   ├── product.py               # Mahsulotlar va mahsulot rasmlari
│   ├── image.py                 # Bot orqali kelgan ishlatilmagan rasmlar
│   ├── cart.py                  # Savat
│   ├── order.py                 # Buyurtmalar va buyurtma mahsulotlari
│   ├── admin.py                 # Adminlar ro'yxati
│   └── settings.py              # Do'kon sozlamalari (white-label)
├── api/
│   ├── deps.py                  # DB va Auth dependencylari
│   └── routes/
│       ├── health.py            # /health (self-ping va status)
│       ├── images.py            # /images/{file_id} (Telegram rasm proksi)
│       ├── webhook.py           # /telegram-webhook (Telegram bot webhook)
│       ├── store.py             # /api/store-settings (Mijoz uchun sozlamalar)
│       ├── categories.py        # /api/categories
│       ├── products.py          # /api/products
│       ├── cart.py              # /api/cart (Savat amallari)
│       ├── orders.py            # /api/orders (Buyurtma berish va tarix)
│       └── admin/               # Admin API endpointlari
│           ├── settings.py      # PATCH /api/admin/store-settings
│           ├── categories.py    # Kategoriyalar CRUD
│           ├── products.py      # Mahsulotlar CRUD & guruhga e'lon
│           ├── images.py        # Ishlatilmagan rasmlar galereyasi
│           └── orders.py        # Buyurtmalar boshqaruvi va status o'zgartirish
├── frontend/                    # Mijoz Telegram Mini App
│   ├── index.html
│   ├── css/style.css
│   └── js/
│       ├── api.js
│       ├── cart.js
│       └── app.js
├── frontend-admin/              # Admin Telegram Mini App
│   ├── index.html
│   ├── css/admin.css
│   └── js/
│       ├── admin-api.js
│       └── admin.js
├── scripts/
│   ├── schema.sql               # Supabase / PostgreSQL to'liq SQL jadval sxemasi
│   └── init_db.py               # Bazani dasturiy yaratish va admin kiritish
├── main.py                      # FastAPI asosiy ilovasi va statik fayllar mounti
├── requirements.txt             # Kerakli Python kutubxonalari
├── .env.example                 # Muhit o'zgaruvchilari namunasi
└── README.md                    # To'liq yo'riqnoma
```

---

## ⚙️ O'rnatish va Ishga Tushirish

### 1. Ma'lumotlar bazasini tayyorlash (Supabase)
1. [Supabase.com](https://supabase.com) saytiga kiring va yangi loyiha (New Project) oching.
2. Chap menyudan **SQL Editor** bo'limiga o'ting.
3. Loyihadagi `scripts/schema.sql` fayli tarkibini ko'chirib o'tkazing va **Run** tugmasini bosing.
4. Supabase loyihangizning **Project Settings -> Database** bo'limiga o'tib, **Connection string (URI)** ni nusxalab oling (masalan: `postgresql://postgres.[ref]:[password]@aws-0-eu-central-1.pooler.supabase.com:6543/postgres`).

### 2. Telegram Botni Sozlash (BotFather)
1. Telegram'da [@BotFather](https://t.me/BotFather) botiga `/newbot` buyrug'ini yuboring va yangi bot yarating.
2. Berilgan `BOT_TOKEN`ni saqlab qo'ying.
3. [@BotFather](https://t.me/BotFather) da `/setmenubutton` buyrug'i orqali botingizning pastki chap burchagiga "🛍 Do'kon" Mini App tugmasini qo'shishingiz mumkin (URL sifatida Render ilovangiz manzilini ko'rsatasiz).

### 3. Adminni Tayinlash
Botingizning admin paneliga kirish va rasm yuklay olishingiz uchun o'z Telegram ID raqamingizni `admins` jadvaliga kiritishingiz kerak:
- O'z ID raqamingizni bilish uchun Telegram'da [@userinfobot](https://t.me/userinfobot) ga yozing.
- Supabase SQL Editor'da quyidagi buyruqni bajaring:
```sql
INSERT INTO admins (telegram_id) VALUES (SIZNING_TELEGRAM_ID_RAQAMINGIZ);
```

---

## 🌐 Render.com'da Bepul Deploy Qilish

1. Kodni GitHub akkauntingizga yuklang (Private yoki Public repository).
2. [Render.com](https://render.com) ga kiring va **New + -> Web Service** ni tanlang.
3. GitHub repository'ingizni ulang.
4. Quyidagi sozlamalarni kiriting:
   - **Name:** `my-telegram-store` (istalgan nom)
   - **Region:** Frankfurt (yoki o'zingizga yaqin hudud)
   - **Branch:** `main`
   - **Runtime:** `Python 3`
   - **Build Command:**
     ```bash
     pip install -r requirements.txt
     ```
   - **Start Command:**
     ```bash
     uvicorn main:app --host 0.0.0.0 --port $PORT
     ```
   - **Plan:** `Free`

5. **Environment Variables** (Muhit O'zgaruvchilari) bo'limiga quyidagilarni kiriting:

| O'zgaruvchi | Tavsif / Namuna |
|-------------|-----------------|
| `BOT_TOKEN` | BotFather'dan olingan token |
| `DATABASE_URL` | Supabase connection string (kod avtomatik `postgresql+asyncpg://` ga o'giradi) |
| `RENDER_EXTERNAL_URL` | Render ilovangiz manzili: `https://my-telegram-store.onrender.com` |
| `WEBHOOK_URL` | `https://my-telegram-store.onrender.com/telegram-webhook` |
| `ADMIN_GROUP_ID` | Yangi buyurtmalar boradigan guruh ID si (masalan `-1001234567890`) |
| `PRODUCT_ANNOUNCE_GROUP_ID` | Mahsulot e'lonlari chiqadigan guruh/kanal ID si |
| `DEBUG` | `False` |

6. **Create Web Service** tugmasini bosing.
   - Render loyihani build qiladi va ishga tushiradi.
   - Startup jarayonida webhook avtomatik tarzda Telegram'ga ulanadi va self-ping xizmati ishga tushadi.

---

## 📱 Qanday Foydalaniladi?

### 1. Admin uchun:
1. Telegram botga `/start` yuboring. Agar siz `admins` jadvalida bo'lsangiz, bot sizga **"⚙️ Admin Panelini ochish"** tugmasini ham chiqaradi.
2. **Rasm yuklash:** Botga to'g'ridan-to'g'ri bir yoki bir nechta rasm yuboring. Bot ularni qabul qilib `uploaded_images` galereyasiga saqlaydi.
3. **Mahsulot qo'shish:** Admin panelini oching → "Mahsulotlar" bo'limiga o'ting → "➕ Yangi mahsulot" tugmasini bosing → Nomi, narxi, kategoriyasini kiriting va quyidagi galereyadan kerakli rasmlarni tanlab saqlang.
4. **Guruhga e'lon qilish:** Mahsulot yonidagi 📢 tugmasini bossangiz, bot belgilangan guruhga rasm, narx va tavsif bilan chiroyli e'lon yuboradi.
5. **Do'kon sozlamalari:** "Sozlamalar" bo'limida do'kon nomi, tavsifi, aloqa telefonini xohlagancha o'zgartiring.
6. **Buyurtmalarni tasdiqlash:** Yangi buyurtma tushganda admin guruhdagi "✅ Tasdiqlash" tugmasini bosishingiz yoki Admin panelidagi "Buyurtmalar" bo'limidan statusni bosqichma-bosqich o'zgartirishingiz mumkin.

### 2. Xaridor (Mijoz) uchun:
1. Botga `/start` bosadi yoki menyudagi "Do'kon" tugmasini bosadi.
2. Katalogda toifalarni saralaydi, mahsulotlarni qidiradi, savatga qo'shadi.
3. Savatdan "Buyurtma berish"ni tanlab, yetkazib berish manzili, telefon raqami va to'lov turini tanlaydi.
4. "Buyurtmalarim" bo'limida o'zining barcha xaridlari holatini real vaqtda rangli statuslarda (Kutilmoqda, Tasdiqlandi, Yetkazilmoqda, Yakunlandi) kuzatib boradi.

---

## 🛠 Mahalliy Kompyuterda Ishga Tushirish (Development)

1. Virtual muhitni yoqing va kutubxonalarni o'rnating:
   ```bash
   pip install -r requirements.txt
   ```
2. `.env.example` faylidan `.env` nusxasini yarating va ma'lumotlarni to'ldiring:
   ```bash
   cp .env.example .env
   ```
3. Ilovani ishga tushiring:
   ```bash
   uvicorn main:app --reload --port 8000
   ```
4. Brauzerda oching:
   - Mijoz Mini App: `http://localhost:8000/`
   - Admin Mini App: `http://localhost:8000/admin/`
   - API Hujjatlari (Swagger): `http://localhost:8000/docs`

---

## 📄 Litsenziya
Ushbu loyiha mustaqil tijoriy shablon (White-Label) sifatida foydalanish va har qanday onlayn do'konlarga qayta deploy qilish uchun to'liq tayyor.
