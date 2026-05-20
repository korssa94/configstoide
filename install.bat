@echo off
chcp 65001 > nul
title Установка PLC Code Generator Pro Max

echo ============================================================
echo 🏭 Автоматическая настройка генератора ПЛК кода
echo ============================================================
echo.

:: 1. Проверяем наличие Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Python не найден в системе. Начинаем автоматическую установку...
    
    :: Использование системного установщика Windows
    winget install Python.Python.3.11 --exact --silent --ensure-path
    
    if %errorlevel% neq 0 (
        echo [ОШИБКА] Не удалось автоматически установить Python через winget.
        echo Пожалуйста, установите Python 3.11 вручную и перезапустите скрипт.
        pause
        exit /b
    )
    
    echo [ОК] Python успешно установлен!
    echo [КРИТИЧНО] Из-за особенностей Windows, пожалуйста, ЗАКРОЙТЕ это окно 
    echo            и ЗАПУСТИТЕ install.bat заново, чтобы применились переменные PATH.
    pause
    exit /b
)

echo [ОК] Python обнаружен в системе.

:: 2. Создаем виртуальное окружение .venv в корне проекта
if not exist .venv (
    echo [INFO] Создаем изолированное окружение .venv...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [ОШИБКА] Не удалось создать .venv.
        pause
        exit /b
    )
)

echo [ОК] Изолированное окружение готово.
echo.
echo ============================================================
echo 📦 Установка необходимых библиотек...
echo ============================================================
echo.

:: 3. Активируем окружение и ставим зависимости
call .venv\Scripts\activate.bat

echo [INFO] Обновляем pip...
python -m pip install --upgrade pip >nul 2>&1

if exist .services\requirements.txt (
    echo [INFO] Накатываем библиотеки из .services\requirements.txt. Подождите...
    pip install -r .services\requirements.txt
    
    if %errorlevel% eq 0 (
        echo.
        echo ============================================================
        echo ✨ УСТАНОВКА ЗАВЕРШЕНА УСПЕШНО!
        echo Теперь вы можете запускать приложение через invisible_start.vbs
        echo ============================================================
    ) else (
        echo [ОШИБКА] Не удалось установить библиотеки. Проверьте интернет-соединение.
    )
) else (
    echo [ВНИМАНИЕ] Файл requirements.txt не найден в папке .services! Переменные не установлены.
)

echo.
pause