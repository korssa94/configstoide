@echo off
chcp 65001 >nul
title DEBUG PLC Generator
cd /d "%~dp0"

echo 1. Проверка пути: %cd%
echo 2. Проверка Python:
python --version
if %errorlevel% neq 0 (
    echo [ОШИБКА] Python не найден в системе!
    pause
    exit
)

echo 3. Попытка запуска Streamlit...
python -m streamlit run app.py
pause