# 🎵 ربات موزیک تلگرام

ربات تلگرامی برای پخش موزیک و ویدیو در **ویدیو کال گروه** — با پشتیبانی از یوتیوب، فایل‌های صوتی، و صف پخش.

---

## ✨ قابلیت‌ها

| دستور | عملکرد |
|-------|---------|
| `پخش [نام آهنگ]` | جستجو در یوتیوب و پخش در ویدیو کال |
| `پخش [لینک یوتیوب]` | پخش مستقیم از لینک یوتیوب |
| `پخش` (ریپلای روی فایل) | پخش فایل صوتی/موزیک ارسال‌شده |
| `رد` | رد کردن آهنگ فعلی |
| `توقف` | توقف کامل پخش |
| `پخش_دوباره` | پخش دوباره آهنگ فعلی از ابتدا |
| `صف` | نمایش صف پخش |
| `راهنما` | نمایش راهنما |

> همه دستورات با یا بدون `/` کار می‌کنند.

---

## 🔧 پیش‌نیازها

- Python 3.10+
- FFmpeg
- حساب توسعه‌دهنده تلگرام (my.telegram.org)
- ربات تلگرام (BotFather)

---

## ⚙️ تنظیمات اولیه

### ۱. دریافت API_ID و API_HASH

1. به [my.telegram.org](https://my.telegram.org) بروید
2. وارد شوید و به بخش **API development tools** بروید
3. یک اپلیکیشن جدید بسازید
4. `api_id` و `api_hash` را یادداشت کنید

### ۲. ساخت ربات در BotFather

1. در تلگرام به `@BotFather` بروید
2. دستور `/newbot` را بفرستید
3. نام و نام کاربری ربات را وارد کنید
4. **توکن** دریافتی را یادداشت کنید

### ۳. غیرفعال کردن حریم خصوصی ربات در گروه‌ها

برای اینکه ربات پیام‌های بدون `/` (مثل `پخش`) را ببیند:

1. در `@BotFather` دستور `/mybots` را بزنید
2. ربات خود را انتخاب کنید
3. **Bot Settings** → **Group Privacy** → **Turn off**

### ۴. ساخت فایل `.env`

```bash
cp .env.example .env
```

فایل `.env` را ویرایش کنید:

```env
API_ID=12345678
API_HASH=abcdef1234567890abcdef1234567890
BOT_TOKEN=123456789:AAFxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

## 🚀 اجرای محلی

```bash
# نصب وابستگی‌ها
pip install -r requirements.txt

# اجرا
python main.py
```

---

## 🌐 دیپلوی روی Hetzner

### ۱. ساخت سرور

1. در [Hetzner Cloud](https://console.hetzner.cloud) وارد شوید
2. یک سرور **CX22** (2 vCPU, 4 GB RAM) با سیستم‌عامل **Ubuntu 22.04** بسازید
3. به سرور SSH بزنید:

```bash
ssh root@YOUR_SERVER_IP
```

### ۲. نصب Docker

```bash
apt-get update
apt-get install -y docker.io docker-compose-plugin
systemctl enable --now docker
```

### ۳. انتقال پروژه به سرور

**روش اول — git (توصیه‌شده):**
```bash
git clone https://github.com/YOUR_USERNAME/telegram-music.git
cd telegram-music
```

**روش دوم — scp:**
```bash
# از کامپیوتر محلی خود:
scp -r ./telegram-music root@YOUR_SERVER_IP:/root/
```

### ۴. ساخت فایل `.env` روی سرور

```bash
cd /root/telegram-music
cp .env.example .env
nano .env   # مقادیر را وارد کنید
```

### ۵. اجرا با Docker Compose

```bash
docker compose up -d --build
```

بررسی لاگ‌ها:
```bash
docker compose logs -f
```

### ۶. به‌روزرسانی ربات

```bash
git pull
docker compose up -d --build
```

---

## 📌 نحوه استفاده در گروه

1. ربات را به گروه اضافه کنید و **ادمین** کنید
2. یک **ویدیو کال** در گروه شروع کنید
3. دستور `پخش` را بزنید:

```
پخش شادمهر عقیلی
پخش https://youtu.be/dQw4w9WgXcQ
```

4. ربات وارد ویدیو کال می‌شود و موزیک پخش می‌کند
5. همه اعضا می‌توانند دستورات را استفاده کنند

---

## 🗂 ساختار پروژه

```
telegram-music/
├── main.py              # نقطه ورود برنامه
├── config.py            # پیکربندی از متغیرهای محیطی
├── requirements.txt     # وابستگی‌های Python
├── Dockerfile           # ساخت image داکر
├── docker-compose.yml   # اجرا با داکر
├── .env.example         # نمونه متغیرهای محیطی
├── handlers/
│   └── play.py          # هندلرهای دستورات
└── utils/
    ├── queue.py         # مدیریت صف پخش
    └── ytdl.py          # دانلود از یوتیوب
```

---

## ⚠️ نکات مهم

- **ویدیو کال باید قبلاً شروع شده باشد** — ربات به ویدیو کال موجود متصل می‌شود، خودش آن را نمی‌سازد
- فایل‌های دانلود‌شده در پوشه `downloads/` ذخیره می‌شوند
- سشن ربات در پوشه `sessions/` ذخیره می‌شود (در داکر با volume نگهداری می‌شود)
