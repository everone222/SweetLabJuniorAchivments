"""SweetLab API — FastAPI бекенд для Telegram Mini App та адмін-панелі."""

import json
import os
import threading
from typing import Any

import sqlite3
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

try:  # запуск як пакет: from backend.main import app
    from .database import (
        db_cursor,
        ensure_seed,
        get_or_create_user,
        init_db,
        now_iso,
        row_to_ingredient,
        row_to_order,
    )
except ImportError:  # локальний запуск: python main.py з папки backend
    from database import (
        db_cursor,
        ensure_seed,
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
ensure_seed()

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


CATEGORIES = {"base", "filling", "topping"}


class IngredientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    category: str
    price: float = Field(ge=0)
    stock: int = Field(default=0, ge=0)
    is_active: bool = True


class IngredientUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    category: str | None = None
    stock: int | None = Field(default=None, ge=0)
    is_active: bool | None = None
    price: float | None = Field(default=None, ge=0)


def clean_ingredient_fields(payload: Any, *, creating: bool = False) -> tuple[list[str], list[Any]]:
    """Підготувати безпечні поля для SQL оновлення/створення."""
    updates: list[str] = []
    values: list[Any] = []

    name = getattr(payload, "name", None)
    if name is not None:
        name = name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="Назва не може бути порожньою")
        updates.append("name = ?")
        values.append(name)
    elif creating:
        raise HTTPException(status_code=400, detail="Вкажи назву")

    category = getattr(payload, "category", None)
    if category is not None:
        category = category.strip().lower()
        if category not in CATEGORIES:
            raise HTTPException(
                status_code=400,
                detail="Категорія має бути base, filling або topping",
            )
        updates.append("category = ?")
        values.append(category)
    elif creating:
        raise HTTPException(status_code=400, detail="Вкажи категорію")

    for field in ("price", "stock"):
        value = getattr(payload, field, None)
        if value is not None:
            updates.append(f"{field} = ?")
            values.append(value)
        elif creating:
            raise HTTPException(status_code=400, detail=f"Вкажи {field}")

    is_active = getattr(payload, "is_active", None)
    if is_active is not None:
        updates.append("is_active = ?")
        values.append(1 if is_active else 0)
    elif creating:
        updates.append("is_active = ?")
        values.append(1)

    return updates, values


def get_ingredient_row(ingredient_id: int) -> dict[str, Any]:
    with db_cursor() as cur:
        cur.execute("SELECT * FROM ingredients WHERE id = ?", (ingredient_id,))
        row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Інгредієнт не знайдено")
    return row_to_ingredient(row)


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


@app.post("/api/admin/ingredients", status_code=201)
def create_ingredient(payload: IngredientCreate) -> dict[str, Any]:
    updates, values = clean_ingredient_fields(payload, creating=True)
    columns = ", ".join(u.split(" = ")[0] for u in updates)
    placeholders = ", ".join("?" for _ in values)
    try:
        with db_cursor(commit=True) as cur:
            cur.execute(
                f"INSERT INTO ingredients ({columns}) VALUES ({placeholders})",
                values,
            )
            ingredient_id = cur.lastrowid
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Позиція з такою назвою вже є")

    return get_ingredient_row(ingredient_id)


@app.get("/api/admin/ingredients/{ingredient_id}")
def get_ingredient(ingredient_id: int) -> dict[str, Any]:
    return get_ingredient_row(ingredient_id)


@app.patch("/api/admin/ingredients/{ingredient_id}")
def update_ingredient(ingredient_id: int, payload: IngredientUpdate) -> dict[str, Any]:
    get_ingredient_row(ingredient_id)
    updates, values = clean_ingredient_fields(payload)

    if not updates:
        raise HTTPException(status_code=400, detail="Немає що оновлювати")

    values.append(ingredient_id)
    try:
        with db_cursor(commit=True) as cur:
            cur.execute(f"UPDATE ingredients SET {', '.join(updates)} WHERE id = ?", values)
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Позиція з такою назвою вже є")

    return get_ingredient_row(ingredient_id)


@app.delete("/api/admin/ingredients/{ingredient_id}")
def delete_ingredient(ingredient_id: int) -> dict[str, Any]:
    get_ingredient_row(ingredient_id)
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM ingredients WHERE id = ?", (ingredient_id,))
    return {"success": True, "id": ingredient_id}


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
