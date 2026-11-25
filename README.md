# 🍫 SweetLab — Telegram Mini App + Адмін-панель

Міні-гра кастомізації шоколаду в Telegram та окрема веб-панель адміністратора.

**Стек:** Python 3 · FastAPI · SQLite (stdlib `sqlite3`) · Telegram Bot API · HTML/CSS/JS (без збірки)
**Дизайн:** тепла шоколадно-карамельна палітра, м'які тіні, плавні мікроанімації, mobile-first.

## Швидкий старт

```powershell
cd D:\my-app\backend

# 1. (одноразово) залежності
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt

# 2. (одноразово) база + інгредієнти
.\venv\Scripts\python.exe seed.py

# 3. запуск
.\venv\Scripts\python.exe -m uvicorn main:app --reload --port 5000
```

Або просто подвійний клік на `start.bat` у корені проєкту.

| Що | Адреса |
|---|---|
| Міні-гра (TMA) | http://localhost:5000/app |
| Адмін-панель | http://localhost:5000/admin |
| Swagger / API docs | http://localhost:5000/docs |
| Healthcheck | http://localhost:5000/health |

## Структура

```
D:\my-app\
├── start.bat                 # запуск у 1 клік
├── README.md
├── PLAN.md                   # покроковий план/статус
└── backend\
    ├── main.py               # FastAPI: API + бот + роздача інтерфейсів
    ├── database.py           # sqlite3: схема, хелпери
    ├── seed.py               # початкові інгредієнти
    ├── smoke_test.py         # перевірка API
    ├── requirements.txt
    ├── .env                  # BOT_TOKEN, DATABASE_URL, WEBAPP_URL
    ├── sweetlab.db           # база (створюється автоматично)
    └── static\
        ├── tma\index.html    # міні-гра
        └── admin\index.html  # адмін-панель
```

## API

### Клієнт (міні-гра)
| Метод | Шлях | Призначення |
|---|---|---|
| GET | `/api/ingredients` | активні інгредієнти з цінами та залишками |
| POST | `/api/orders` | створити замовлення |
| GET | `/api/orders/user/{telegram_id}` | історія замовлень користувача |

### Адмін
| Метод | Шлях | Призначення |
|---|---|---|
| GET | `/api/admin/stats` | користувачі, замовлення, список |
| PATCH | `/api/admin/orders/{id}/status` | змінити статус |
| GET | `/api/admin/ingredients` | усі інгредієнти |
| PATCH | `/api/admin/ingredients/{id}` | залишок / ціна / доступність |

## Telegram

Бот: **@SweetLabJA_bot** (polling, команда `/start` → кнопка відкриття міні-гри).

> ⚠️ Telegram приймає лише **HTTPS**-адресу для Web App. Для тесту всередині Telegram
> підніміть тунель (`ngrok http 5000`) і вкажіть у `backend/.env`:
> `WEBAPP_URL="https://<ваш-домен>.ngrok-free.app/app"`, після чого перезапустіть сервер.
> Локально у браузері все працює без тунелю.

## Тестування

```powershell
cd backend
.\venv\Scripts\python.exe smoke_test.py
```

Скрипт перевіряє healthcheck, інгредієнти, створення замовлення, зміну статусу,
оновлення складу та доступність сторінок `/app` і `/admin`.

## Деплой на хостинг (Pella / Render / Railway / будь-який Python-хостинг)

Команда запуску (**Start command**):

```bash
python app.py
```

або через Procfile (вже є в корені): `web: python app.py`.

- Застосунок слухає `0.0.0.0` і порт із змінної `PORT` (за замовчуванням `8000`).
- Кореневі файли `app.py`, `main.py`, `Procfile`, `requirements.txt`, `runtime.txt` — обов'язкові.
- ⚠️ `.env` не лежить у Git (там токен бота). На хостингу задайте змінні оточення вручну:
  - `BOT_TOKEN` — токен бота (інакше бот вимкнеться, але сайт працюватиме);
  - `WEBAPP_URL` — **HTTPS**-адреса вигляду `https://your-app.onrender.com/app`;
  - `DATABASE_URL` — залиште `sqlite:///./sweetlab.db` або задайте свою.
- Не вказуйте як стартову команду `cleanup_demo.py` — це одноразовий допоміжний скрипт, його видалено.
