"""Доступ до бази даних на базі вбудованого sqlite3 (без компільованих залежностей)."""

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Iterator

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sweetlab.db")

# Підтримуємо формат sqlite:///./sweetlab.db та прямий шлях
DB_PATH = DATABASE_URL.replace("sqlite:///", "") if DATABASE_URL.startswith("sqlite") else DATABASE_URL

STATUSES = ("created", "preparing", "delivering", "completed")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db_cursor(commit: bool = False) -> Iterator[sqlite3.Cursor]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        yield cur
        if commit:
            conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with db_cursor(commit=True) as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL UNIQUE,
                username TEXT,
                first_name TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS ingredients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL,
                price REAL NOT NULL DEFAULT 0,
                stock INTEGER NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                recipe TEXT NOT NULL,
                total_price REAL NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'created',
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            """
        )


# Початковий асортимент — щоб хостинг із чистою базою одразу мав дані.
SEED_INGREDIENTS = [
    {"name": "Чорний шоколад 72%", "category": "base", "price": 50, "stock": 100},
    {"name": "Молочний шоколад", "category": "base", "price": 45, "stock": 120},
    {"name": "Білий шоколад", "category": "base", "price": 45, "stock": 80},
    {"name": "Рожевий шоколад (Рубі)", "category": "base", "price": 60, "stock": 50},
    {"name": "Горіхи фундук", "category": "filling", "price": 20, "stock": 200},
    {"name": "Мигдаль", "category": "filling", "price": 22, "stock": 150},
    {"name": "Сушена малина", "category": "filling", "price": 25, "stock": 90},
    {"name": "Солона карамель", "category": "filling", "price": 18, "stock": 110},
    {"name": "Шматочки манго", "category": "filling", "price": 20, "stock": 70},
    {"name": "Золотий харчовий пил", "category": "topping", "price": 35, "stock": 40},
    {"name": "Кокосова стружка", "category": "topping", "price": 10, "stock": 300},
    {"name": "Їстівні квіти", "category": "topping", "price": 30, "stock": 60},
    {"name": "Какао-боби (крихта)", "category": "topping", "price": 15, "stock": 130},
]


def ensure_seed() -> None:
    """Додати стартові інгредієнти, якщо база ще порожня."""
    init_db()
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT COUNT(*) AS c FROM ingredients")
        if cur.fetchone()["c"]:
            return
        for item in SEED_INGREDIENTS:
            cur.execute(
                "INSERT OR IGNORE INTO ingredients (name, category, price, stock, is_active) "
                "VALUES (?, ?, ?, ?, 1)",
                (item["name"], item["category"], item["price"], item["stock"]),
            )


def now_iso() -> str:
    return datetime.utcnow().isoformat()


def row_to_ingredient(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "category": row["category"],
        "price": row["price"],
        "stock": row["stock"],
        "is_active": bool(row["is_active"]),
    }


def row_to_order(row: sqlite3.Row, user: dict[str, Any] | None = None) -> dict[str, Any]:
    order = {
        "id": row["id"],
        "userId": row["user_id"],
        "recipe": json.loads(row["recipe"]),
        "totalPrice": row["total_price"],
        "status": row["status"],
        "createdAt": row["created_at"],
    }
    if user is not None:
        order["user"] = user
    return order


def get_or_create_user(telegram_id: int, username: str | None, first_name: str | None) -> dict[str, Any]:
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        row = cur.fetchone()
        if row is None:
            cur.execute(
                "INSERT INTO users (telegram_id, username, first_name, created_at) VALUES (?, ?, ?, ?)",
                (telegram_id, username, first_name, now_iso()),
            )
            cur.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
            row = cur.fetchone()
    return {
        "id": row["id"],
        "telegramId": str(row["telegram_id"]),
        "username": row["username"],
        "firstName": row["first_name"],
        "createdAt": row["created_at"],
    }
