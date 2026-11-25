"""SweetLab API — FastAPI бекенд для Telegram Mini App та адмін-панелі."""

import json
import os
import threading
from typing import Any

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from database import (
    db_cursor,
    get_or_create_user,
    init_db,
    now_iso,
    row_to_ingredient,
    row_to_order,
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
WEBAPP_URL = os.getenv("WEBAPP_URL", "http://localhost:5000/app")
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

init_db()

app = FastAPI(title="SweetLab API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------- Схеми запитів -------------------------
class OrderCreate(BaseModel):
    telegram_id: int
    username: str | None = "guest"
    first_name: str | None = "Guest"
    recipe: Any
    total_price: float = Field(ge=0)


class StatusUpdate(BaseModel):
    status: str


class IngredientUpdate(BaseModel):
    stock: int | None = Field(default=None, ge=0)
    is_active: bool | None = None
    price: float | None = Field(default=None, ge=0)


# ------------------------- Telegram бот -------------------------
def tg_api(method: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    response = requests.post(url, json=payload or {}, timeout=40)
    return response.json()


def send_welcome(chat_id: int) -> None:
    tg_api(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": (
                "🍫 *Ласкаво просимо до SweetLab!*\n\n"
                "Створи власну плитку шоколаду ручної роботи: "
                "обе­ри основу, додай начинки та декор."
            ),
            "parse_mode": "Markdown",
            "reply_markup": {
                "inline_keyboard": [
                    [{"text": "✨ Створити шоколад", "web_app": {"url": WEBAPP_URL}}]
                ]
            },
        },
    )


def bot_loop() -> None:
    if not BOT_TOKEN:
        print("[bot] BOT_TOKEN не задано — бот вимкнено")
        return

    me = tg_api("getMe")
    if not me.get("ok"):
        print(f"[bot] Не вдалося авторизуватися: {me.get('description')}")
        return
    print(f"[bot] Авторизовано як @{me['result'].get('username')}")

    menu = tg_api(
        "setChatMenuButton",
        {"menu_button": {"type": "web_app", "text": "Шоколад", "web_app": {"url": WEBAPP_URL}}},
    )
    if not menu.get("ok"):
        print(f"[bot] Кнопку меню не встановлено (потрібен HTTPS): {menu.get('description')}")

    offset = 0
    print("[bot] Очікую повідомлення (polling)...")
    while True:
        try:
            data = tg_api("getUpdates", {"offset": offset, "timeout": 25})
            if not data.get("ok"):
                error = data.get("description", "")
                if "409" in error or "terminated by other" in error:
                    print("[bot] Конфлікт polling: бот уже запущений в іншому процесі")
                    return
                continue
            for update in data.get("result", []):
                offset = update["update_id"] + 1
                message = update.get("message") or {}
                text = (message.get("text") or "").strip()
                if text.startswith("/start"):
                    send_welcome(message["chat"]["id"])
        except Exception:
            # мережеві збої — просто продовжуємо
            continue


threading.Thread(target=bot_loop, daemon=True).start()


# ------------------------- API -------------------------
@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/ingredients")
def get_ingredients() -> list[dict[str, Any]]:
    with db_cursor() as cur:
        cur.execute("SELECT * FROM ingredients WHERE is_active = 1 ORDER BY id")
        return [row_to_ingredient(row) for row in cur.fetchall()]


@app.post("/api/orders", status_code=201)
def create_order(payload: OrderCreate) -> dict[str, Any]:
    user = get_or_create_user(payload.telegram_id, payload.username, payload.first_name)

    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO orders (user_id, recipe, total_price, status, created_at) VALUES (?, ?, ?, 'created', ?)",
            (user["id"], json.dumps(payload.recipe, ensure_ascii=False), payload.total_price, now_iso()),
        )
        order_id = cur.lastrowid
        cur.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        row = cur.fetchone()

    return row_to_order(row, user)


@app.get("/api/orders/user/{telegram_id}")
def get_user_orders(telegram_id: int) -> list[dict[str, Any]]:
    with db_cursor() as cur:
        cur.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
        user = cur.fetchone()
        if user is None:
            return []
        cur.execute(
            "SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC", (user["id"],)
        )
        return [row_to_order(row) for row in cur.fetchall()]


@app.get("/api/admin/stats")
def admin_stats() -> dict[str, Any]:
    with db_cursor() as cur:
        cur.execute("SELECT COUNT(*) AS c FROM users")
        users_count = cur.fetchone()["c"]
        cur.execute("SELECT COUNT(*) AS c FROM orders")
        orders_count = cur.fetchone()["c"]
        cur.execute(
            """
            SELECT o.*, u.telegram_id, u.username, u.first_name
            FROM orders o JOIN users u ON u.id = o.user_id
            ORDER BY o.created_at DESC
            """
        )
        orders = []
        for row in cur.fetchall():
            user = {
                "id": row["user_id"],
                "telegramId": str(row["telegram_id"]),
                "username": row["username"],
                "firstName": row["first_name"],
            }
            orders.append(row_to_order(row, user))

    return {"usersCount": users_count, "ordersCount": orders_count, "orders": orders}


@app.patch("/api/admin/orders/{order_id}/status")
def update_order_status(order_id: int, payload: StatusUpdate) -> dict[str, Any]:
    allowed = {"created", "preparing", "delivering", "completed"}
    if payload.status not in allowed:
        raise HTTPException(status_code=400, detail=f"Невідомий статус: {payload.status}")

    with db_cursor(commit=True) as cur:
        cur.execute("SELECT id FROM orders WHERE id = ?", (order_id,))
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="Замовлення не знайдено")
        cur.execute("UPDATE orders SET status = ? WHERE id = ?", (payload.status, order_id))

    return {"success": True, "id": order_id, "status": payload.status}


@app.get("/api/admin/ingredients")
def admin_ingredients() -> list[dict[str, Any]]:
    with db_cursor() as cur:
        cur.execute("SELECT * FROM ingredients ORDER BY category, id")
        return [row_to_ingredient(row) for row in cur.fetchall()]


@app.patch("/api/admin/ingredients/{ingredient_id}")
def update_ingredient(ingredient_id: int, payload: IngredientUpdate) -> dict[str, Any]:
    updates: list[str] = []
    values: list[Any] = []

    if payload.stock is not None:
        updates.append("stock = ?")
        values.append(payload.stock)
    if payload.price is not None:
        updates.append("price = ?")
        values.append(payload.price)
    if payload.is_active is not None:
        updates.append("is_active = ?")
        values.append(1 if payload.is_active else 0)

    if not updates:
        raise HTTPException(status_code=400, detail="Немає що оновлювати")

    values.append(ingredient_id)
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT id FROM ingredients WHERE id = ?", (ingredient_id,))
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="Інгредієнт не знайдено")
        cur.execute(f"UPDATE ingredients SET {', '.join(updates)} WHERE id = ?", values)

    return {"success": True}


# ------------------------- Статичні інтерфейси -------------------------
@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse(url="/app")


@app.get("/app")
def tma_app() -> FileResponse:
    return FileResponse(os.path.join(STATIC_DIR, "tma", "index.html"))


@app.get("/admin")
def admin_app() -> FileResponse:
    return FileResponse(os.path.join(STATIC_DIR, "admin", "index.html"))


if os.path.isdir(os.path.join(STATIC_DIR, "tma")):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
