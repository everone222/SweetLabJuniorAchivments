"""Наповнення бази початковими інгредієнтами."""

from database import db_cursor, init_db

INGREDIENTS = [
    # Основи
    {"name": "Чорний шоколад 72%", "category": "base", "price": 50, "stock": 100},
    {"name": "Молочний шоколад", "category": "base", "price": 45, "stock": 120},
    {"name": "Білий шоколад", "category": "base", "price": 45, "stock": 80},
    {"name": "Рожевий шоколад (Рубі)", "category": "base", "price": 60, "stock": 50},
    # Начинки
    {"name": "Горіхи фундук", "category": "filling", "price": 20, "stock": 200},
    {"name": "Мигдаль", "category": "filling", "price": 22, "stock": 150},
    {"name": "Сушена малина", "category": "filling", "price": 25, "stock": 90},
    {"name": "Солона карамель", "category": "filling", "price": 18, "stock": 110},
    {"name": "Шматочки манго", "category": "filling", "price": 20, "stock": 70},
    # Декор
    {"name": "Золотий харчовий пил", "category": "topping", "price": 35, "stock": 40},
    {"name": "Кокосова стружка", "category": "topping", "price": 10, "stock": 300},
    {"name": "Їстівні квіти", "category": "topping", "price": 30, "stock": 60},
    {"name": "Какао-боби (крихта)", "category": "topping", "price": 15, "stock": 130},
]


def seed() -> None:
    init_db()
    added = 0
    with db_cursor(commit=True) as cur:
        for item in INGREDIENTS:
            cur.execute("SELECT id FROM ingredients WHERE name = ?", (item["name"],))
            if cur.fetchone() is None:
                cur.execute(
                    "INSERT INTO ingredients (name, category, price, stock, is_active) VALUES (?, ?, ?, ?, 1)",
                    (item["name"], item["category"], item["price"], item["stock"]),
                )
                added += 1
        cur.execute("SELECT COUNT(*) AS c FROM ingredients")
        total = cur.fetchone()["c"]
    print(f"Seed OK: додано {added} нових інгредієнтів, всього в базі: {total}")


if __name__ == "__main__":
    seed()
