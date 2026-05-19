@echo off
chcp 65001 >nul
cd /d "%~dp0"

:: Удаляем старый лог для чистоты эксперимента
if exist server_log.txt del server_log.txt

:: Указываем полный путь к твоему Python.
:: Добавляем флаг gatherUsageStats, чтобы Streamlit не задавал лишних вопросов в фоне.
"C:\Users\korss\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m streamlit run app.py --server.headless true --browser.gatherUsageStats false > server_log.txt 2>&1