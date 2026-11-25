@echo off
setlocal
cd /d "%~dp0backend"

if not exist "venv\Scripts\python.exe" (
    echo [1/3] Створюю віртуальне середовище...
    python -m venv venv
    if errorlevel 1 goto :fail
    echo [2/3] Встановлюю залежності...
    venv\Scripts\python.exe -m pip install --upgrade pip --quiet
    venv\Scripts\python.exe -m pip install -r requirements.txt
    if errorlevel 1 goto :fail
)

if not exist "sweetlab.db" (
    echo [3/3] Наповнюю базу інгредієнтами...
    venv\Scripts\python.exe seed.py
)

echo.
echo   Міні-гра:      http://localhost:5000/app
echo   Адмін-панель:  http://localhost:5000/admin
echo   API docs:      http://localhost:5000/docs
echo.
venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 5000 --reload
goto :eof

:fail
echo.
echo Помилка встановлення. Перевірте, чи встановлено Python 3.10+ і додано його в PATH.
pause
