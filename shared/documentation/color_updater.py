import xlwings as xw
import os

def update_configurator_colors(filepath, rows_to_color, config_class, logger):
    """
    Универсальная функция покраски ячеек.
    Получает готовую карту строк от парсера и точечно красит резервы в Excel через xlwings.
    """
    if not rows_to_color:
        logger("🎨 Нет данных для изменения цветов ячеек.", "INFO")
        return

    try:
        filename = os.path.basename(filepath)
        is_background = False
        
        # Пытаемся найти уже открытый файл в активном окне
        try:
            wb = xw.books[filename]
            app = wb.app
            logger(f"🔗 Подключились к открытому {filename} для покраски", "INFO")
        except Exception:
            # Если Excel закрыт или файл не открыт, запускаем невидимый фоновый процесс
            app = xw.App(visible=False)
            wb = app.books.open(filepath)
            is_background = True
            logger(f"📁 Открыли {filename} в фоновом режиме для покраски", "INFO")
            
        app.screen_updating = False
        colored_count = 0
        
        for sheet_name, rows_dict in rows_to_color.items():
            if sheet_name not in [sh.name for sh in wb.sheets]:
                continue
                
            ws = wb.sheets[sheet_name]
            
            # Читаем до 100 колонок, чтобы точно захватить BP и всё, что дальше
            headers = ws.range((config_class.HEADER_ROW, 1), (config_class.HEADER_ROW, 100)).value
            if not headers: continue
            
            # Собираем карту заголовков, беря строго ПЕРВОЕ совпадение (основную колонку)
            header_map = {}
            for idx, val in enumerate(headers):
                if val:
                    val_str = str(val).strip()
                    if val_str not in header_map:
                        header_map[val_str] = idx + 1
            
            col_alg_name = getattr(config_class, 'COL_ALG_NAME', getattr(config_class, 'COL_PARAM_CODE', None))
            col_alg = header_map.get(col_alg_name)
            
            if not col_alg: continue
            
            # Выделяем списки строк для аудита
            reserve_rows = [r for r, is_res in rows_dict.items() if is_res]
            
            if reserve_rows:
                sample_rows = reserve_rows[:15]
                logger(f"📋 Лист '{sheet_name}': найдено {len(reserve_rows)} резервов.", "INFO")
            else:
                logger(f"📋 Лист '{sheet_name}': резервные строки не обнаружены", "INFO")
            
            # Перебор строк с покраской всей строки целиком для обхода ограничений Страничного режима
            for excel_row, is_reserve in rows_dict.items():
                try:
                    if is_reserve:
                        # Красим всю строку целиком через синтаксис xlwings
                        ws.range(f"{excel_row}:{excel_row}").color = (217, 217, 217)
                        colored_count += 1
                    else:
                        # Снимаем заливку со всей строки
                        ws.range(f"{excel_row}:{excel_row}").color = None
                except Exception:
                    pass

        # Если мы сами открыли скрытый Excel, сохраняем и прибираем за собой
        if is_background:
            wb.save()
            wb.close()
            app.quit()
            logger(f"💾 Фоновый процесс завершен, {filename} сохранен.", "INFO")
        else:
            app.screen_updating = True
            
        logger(f"🎨 Процесс покраски завершен (выделено резервов: {colored_count}).", "INFO")
            
    except Exception as e:
        logger(f"❌ Ошибка xlwings при покраске: {str(e)}", "ERROR")
        try:
            if 'is_background' in locals() and is_background and 'app' in locals():
                app.quit()
            elif 'app' in locals() and not is_background:
                app.screen_updating = True
        except:
            pass