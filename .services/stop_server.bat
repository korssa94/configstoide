@echo off
chcp 65001 >nul
title Остановка фонового сервера
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *streamlit*" >nul 2>&1
taskkill /F /IM python.exe >nul 2>&1
echo Сервер успешно остановлен!
timeout /t 2 >nul