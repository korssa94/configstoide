@echo off
chcp 65001 >nul
:: Переходим в корень проекта из папки .services
cd /d "%~dp0\.."

if exist .services\server_log.txt del .services\server_log.txt

:: Запускаем streamlit СТРОГО через созданный .venv, используя относительный путь!
.venv\Scripts\python.exe -m streamlit run app.py --server.headless true --browser.gatherUsageStats false > .services\server_log.txt 2>&1