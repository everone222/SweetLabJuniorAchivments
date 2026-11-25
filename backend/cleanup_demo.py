"""Одноразове очищення тестових даних після smoke-тестів."""

import sqlite3

conn = sqlite3.connect("sweetlab.db")
cur = conn.cursor()

cur.execute("DELETE FROM orders WHERE user_id IN (SELECT id FROM users WHERE telegram_id = 555001)")
cur.execute("DELETE FROM users WHERE telegram_id = 555001")
cur.execute("UPDATE ingredients SET stock = 100 WHERE name LIKE 'Чорний%'")
cur.execute("UPDATE ingredients SET stock = 120 WHERE name LIKE 'Молочний%'")

conn.commit()

cur.execute("SELECT COUNT(*) FROM orders")
orders = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM users")
users = cur.fetchone()[0]

print(f"Готово: замовлень {orders}, користувачів {users}")
conn.close()
