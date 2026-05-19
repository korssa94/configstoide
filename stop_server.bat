@echo off
chcp 65001 >nul
title Остановка PLC Code Generator

echo ==========================================
echo    Остановка фонового сервера...
echo ==========================================
echo.

:: Убиваем процесс python, который держит streamlit
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *streamlit*" >nul 2>&1
:: На всякий случай убиваем другие зависшие процессы питона
taskkill /F /IM python.exe >nul 2>&1

echo.
echo Сервер успешно остановлен! Оперативная память очищена.
echo.
pause