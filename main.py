"""Альтернативна точка входу: python main.py / uvicorn main:app."""

import os

import uvicorn

from app import app, application  # noqa: F401 — `application` для WSGI-хостингів

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
