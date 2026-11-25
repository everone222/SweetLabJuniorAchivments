"""Точка входу для хостингів.

Локально:   python app.py
Хостинг:    python app.py  (порт береться зі змінної PORT)
WSGI:       application = app
"""

import os

import uvicorn

from backend.main import app

# Аліас для хостингів, які шукають WSGI-об'єкт `application`
application = app


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
