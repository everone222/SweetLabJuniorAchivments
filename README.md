# 🍫 SweetLab — Telegram Mini App + Адмін-панель

Міні-гра кастомізації шоколаду в Telegram та окрема веб-панель адміністратора.

**Стек:** Python 3 · FastAPI · SQLite (stdlib `sqlite3`) · Telegram Bot API · HTML/CSS/JS (без збірки)
**Дизайн:** тепла шоколадно-карамельна палітра, м'які тіні, плавні мікроанімації, mobile-first.

## Live (Render, безкоштовний план)

| Що | Адреса |
|---|---|
| Міні-гра (TMA) | https://sweetlabjuniorachivments.onrender.com/app |
| Адмін-панель | https://sweetlabjuniorachivments.onrender.com/admin |
| Healthcheck | https://sweetlabjuniorachivments.onrender.com/health |

Бот **@SweetLabJA_bot** надсилає кнопку Web App саме на цю адресу.
Сервіс створено з `render.yaml`: `pip install -r requirements.txt` →
`uvicorn app:app --host 0.0.0.0 --port $PORT`, змінні `BOT_TOKEN` і `WEBAPP_URL` задані в Render.

## Нові можливості

- Міні-гра побудована як майстер з 5 окремих екранів:
  **назва плитки → шоколад → начинки → декор → перевірка**.
  Усі варіанти подано списком із цінами та залишками; назву шоколаду можна ввести самостійно.
- В адмін-панелі на вкладці **«Асортимент»** можна додавати нові позиції
  (шоколад/начинка/декор), редагувати назву, категорію, ціну, залишок,
  умикати/вимикати доступність і видаляти позиції.
- Нові API: `POST /api/admin/ingredients`, `GET /api/admin/ingredients/{id}`,
  `PATCH /api/admin/ingredients/{id}`, `DELETE /api/admin/ingredients/{id}`.
  Зміни одразу видно в міні-грі після оновлення сторінки.

> Free-план засинає після 15 хв простою — перший запит може зайняти ~50 с.
> SQLite-база тимчасова: після рестарту 13 інгредієнтів створюються автоматично.

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
- Кореневі файли `app.py`, `database.py`, `main.py`, `tma.html`, `admin.html`,
  `cleanup_demo.py`, `Procfile`, `requirements.txt`, `runtime.txt` — обов'язкові.
  Застосунок працює **навіть якщо хостинг залив лише кореневі файли** (без `backend/` і `static/`).
- `cleanup_demo.py` і `main.py` — сумісні точки входу для старих Start Command на хостингу.
  Усі три команди (`python app.py`, `python main.py`, `python cleanup_demo.py`) запускають той самий сервер.
- База створюється автоматично; 13 стартових інгредієнтів додаються при першому запуску
  лише якщо таблиця порожня (функція `ensure_seed()` у `database.py`).
- ⚠️ `.env` не лежить у Git (там токен бота). На хостингу задайте змінні оточення вручну:
  - `BOT_TOKEN` — токен бота (інакше бот вимкнеться, але сайт працюватиме);
  - `WEBAPP_URL` — **HTTPS**-адреса вигляду `https://your-app.onrender.com/app`;
  - `DATABASE_URL` — залиште `sqlite:///./sweetlab.db` або задайте свою.
