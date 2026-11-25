"""Сумісність зі старим Start Command на хостингу.

У панелі хостингу досі вказано `python cleanup_demo.py`.
Цей файл не очищає нічого — він просто запускає застосунок,
поки ви не зміните команду на `python app.py`.
"""

import os

import uvicorn

from app import app

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
