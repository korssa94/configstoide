import xlwings as xw
import os
from shared.documentation.excel_utils import fix_print_settings

def update_configurator_texts(filepath, parsed_objects, config_class, logger):
    """
    Универсальная функция обновления текстов.
    Работает через сопоставление НОМЕРА СТРОКИ, что дает 100% точность попадания.
    """
    try:
        filename = os.path.basename(filepath)
        is_background = False
        
        try:
            wb = xw.books[filename]
            app = wb.app
            logger(f"🔗 Подключились к открытому {filename} для вставки текста", "INFO")
        except Exception:
            app = xw.App(visible=False)
            wb = app.books.open(filepath)
            is_background = True
            logger(f"📁 Открыли {filename} в фоновом режиме для вставки текста", "INFO")
            
        SHEET_NAME = getattr(config_class, 'SHEET_MAIN', getattr(config_class, 'SHEET_ALARMS', None))
        
        if not SHEET_NAME or SHEET_NAME not in [sheet.name for sheet in wb.sheets]:
            if is_background:
                wb.close()
                app.quit()
            return
            
        ws = wb.sheets[SHEET_NAME]
        app.screen_updating = False
        
        # Читаем заголовки
        headers = ws.range((config_class.HEADER_ROW, 1), (config_class.HEADER_ROW, 50)).value
        if not headers:
            logger("❌ Не удалось прочитать заголовки.", "ERROR")
            return
            
        header_map = {str(val).strip(): idx + 1 for idx, val in enumerate(headers) if val}
        
        # Колонка для определения последней строки
        col_check_name = getattr(config_class, 'COL_ALG_NAME', getattr(config_class, 'COL_PARAM_CODE', None))
        col_check = header_map.get(col_check_name)
        
        if not col_check:
            logger(f"❌ Столбец '{col_check_name}' не найден в шапке!", "ERROR")
            return

        last_row = ws.range((ws.api.Rows.Count, col_check)).end('up').row
        if last_row < config_class.DATA_START_ROW:
            return 
            
        # СОЗДАЕМ СЛОВАРЬ ПО НОМЕРУ СТРОКИ (100% точность сопоставления)
        objects_by_row = {getattr(obj, 'row_number', idx): obj for idx, obj in enumerate(parsed_objects)}
        
        # Количество строк данных
        row_count = last_row - config_class.DATA_START_ROW + 1
        
        fields_to_update = {
            'trigger_text': getattr(config_class, 'COL_CONDITION_TEXT', None),
            'fault_text': getattr(config_class, 'COL_FAULT_TEXT', None),
            'set_text': getattr(config_class, 'COL_SET_TEXT', None),
            'reset_text': getattr(config_class, 'COL_RESET_TEXT', None),
        }
        
        # Читаем только нужные колонки в память
        active_cols = {}
        for obj_attr, config_col_name in fields_to_update.items():
            if config_col_name and config_col_name in header_map:
                col_idx = header_map[config_col_name]
                val = ws.range((config_class.DATA_START_ROW, col_idx), (last_row, col_idx)).value
                active_cols[obj_attr] = {
                    'idx': col_idx,
                    'data': val if isinstance(val, list) else [val]
                }

        if not active_cols:
            logger("⚠️ В конфигураторе не найдено колонок для вставки текста (проверьте шапку).", "WARNING")
            return

        updated_count = 0
        
        # Проходим по всем строкам данных в Excel
        for i in range(row_count):
            excel_row = config_class.DATA_START_ROW + i
            
            # Если для этой строки Excel есть распарсенный объект
            if excel_row in objects_by_row:
                obj = objects_by_row[excel_row]
                updated = False
                
                # Обновляем каждый найденный атрибут (если он не пустой)
                for attr, col_info in active_cols.items():
                    new_text = getattr(obj, attr, None)
                    if new_text:
                        col_info['data'][i] = new_text
                        updated = True
                        
                if updated:
                    updated_count += 1

        # Пакетно записываем измененные колонки обратно
        for col_info in active_cols.values():
            ws.range((config_class.DATA_START_ROW, col_info['idx'])).options(transpose=True).value = col_info['data']
        
        if is_background:
            wb.save()
            wb.close()
            app.quit()
            logger(f"💾 Фоновый процесс завершен, {filename} сохранен.", "INFO")
        else:
            app.screen_updating = True
            
        logger(f"✨ Тексты успешно вставлены (затронуто строк: {updated_count}).", "INFO")
        
    except Exception as e:
        logger(f"❌ Ошибка xlwings при вставке текста: {str(e)}", "ERROR")
        try:
            if 'is_background' in locals() and is_background and 'app' in locals():
                app.quit()
            elif 'app' in locals() and not is_background:
                app.screen_updating = True
        except:
            pass