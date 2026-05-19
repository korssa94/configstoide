import win32com.client
import pythoncom
import os
from settings import AppConfig
from application.settings_manager import load_settings

def update_configurator_document(filepath, parsed_objects, config_class, logger):
    """Универсально заполняет лист 'Документ' данными и вызывает макрос форматирования из надстройки"""
    
    pythoncom.CoInitialize()
    excel = None
    wb = None
    
    try:
        filename = os.path.basename(filepath)
        is_background = False
        
        # 1. Пробуем подключиться к уже открытому Excel
        try:
            excel = win32com.client.GetActiveObject("Excel.Application")
            logger(f"🔗 Подключились к открытому {filename} для сборки Документа", "INFO")
        except:
            excel = win32com.client.Dispatch("Excel.Application")
            is_background = True
            logger(f"📁 Открыли {filename} в фоновом режиме для сборки Документа", "INFO")

        if not is_background:
            try:
                excel.Visible = True
            except:
                pass
        
        # 2. Ищем, не открыт ли уже этот файл
        file_already_open = False
        for opened_wb in excel.Workbooks:
            if os.path.normpath(opened_wb.FullName) == os.path.normpath(filepath):
                wb = opened_wb
                file_already_open = True
                break
        
        if not file_already_open:
            wb = excel.Workbooks.Open(filepath)

        excel.ScreenUpdating = False
        
        # --- УНИВЕРСАЛЬНЫЕ НАСТРОЙКИ ---
        sheet_doc_name = getattr(config_class, 'SHEET_DOC', None)
        sheet_alarms_name = getattr(config_class, 'SHEET_ALARMS', None)
        sheet_internal_name = getattr(config_class, 'SHEET_INTERNAL', None)

        # Проверяем листы
        sheet_names = [sh.Name for sh in wb.Sheets]
        if sheet_doc_name not in sheet_names or not sheet_alarms_name or sheet_alarms_name not in sheet_names:
            if is_background:
                wb.Close(SaveChanges=False)
                excel.Quit()
            else:
                excel.ScreenUpdating = True
            return False
            
        ws_doc = wb.Sheets(sheet_doc_name)
        ws_main = wb.Sheets(sheet_alarms_name)
        ws_tr = wb.Sheets(sheet_internal_name) if sheet_internal_name in sheet_names else None

        # --- НАЧАЛО БЛОКА ПЕРЕНОСА ДАННЫХ ПИТОНОМ ---
        
        # Очистка листа Документ (начиная со 2 строки)
        last_row_doc = ws_doc.Cells(ws_doc.Rows.Count, 1).End(-4162).Row # xlUp = -4162
        if last_row_doc > 1:
            ws_doc.Rows(f"2:{last_row_doc+100}").Clear() # Clear удаляет и значения, и форматы
        
        ws_doc.Columns("A").NumberFormat = "@"

        current_row = 2

        # Копирование Внутренних сигнализаций/данных (Без буфера обмена!)
        if ws_tr:
            tr_last_row = ws_tr.Cells(ws_tr.Rows.Count, 1).End(-4162).Row
            if tr_last_row > 1:
                # Берем диапазон из конфига или A2:K по умолчанию
                tr_range = getattr(config_class, 'INTERNAL_COPY_RANGE', 'A2:K')
                ws_doc.Range(f"{tr_range}{tr_last_row}").Value = ws_tr.Range(f"{tr_range}{tr_last_row}").Value
                current_row = tr_last_row + 1

        # Перенос основных данных и вставка детального текста
        # Используем свойство row_number, чтобы точно сопоставить объект со строкой
        obj_dict = {getattr(obj, 'row_number', i): obj for i, obj in enumerate(parsed_objects)}
        
        # Колонка для поиска последней строки (5 = 'E' по умолчанию)
        col_check = getattr(config_class, 'COL_DOC_CHECK', 5)
        main_last_row = ws_main.Cells(ws_main.Rows.Count, col_check).End(-4162).Row

        for i in range(2, main_last_row + 1):
            col_val = ws_main.Cells(i, col_check).Value
            if not col_val:
                continue
            
            # Универсальный диапазон копирования строки (по умолчанию E:O)
            copy_range_str = getattr(config_class, 'DOC_COPY_RANGE', f"E{i}:O{i}")
            if "{i}" in copy_range_str:
                copy_range_str = copy_range_str.format(i=i)
            
            # Прямое присвоение основной строки
            ws_doc.Range(f"A{current_row}:K{current_row}").Value = ws_main.Range(copy_range_str).Value
            
            if i in obj_dict:
                obj = obj_dict[i]
                
                trigger_cond = getattr(obj, 'trigger_cond', None)
                
                # 1. ГЛАВНОЕ УСЛОВИЕ: если кода нет — вообще ничего не пишем во вторую строку
                if not trigger_cond:
                    current_row += 1
                    continue
                
                # Вспомогательная функция очистки "мусора"
                def fmt_txt(val):
                    return str(val or "").replace("_x000D_", "").replace("\r", "").strip()

                detail_parts = []
                
                # Условие (всегда добавляем, так как мы выше проверили наличие trigger_cond)
                trigger_text = getattr(obj, 'trigger_text', '')
                detail_parts.append(f"Условие (код): {trigger_cond}\n{fmt_txt(trigger_text)}")
                
                # Неисправность (только для АС и если есть код)
                fault_cond = getattr(obj, 'fault_cond', None)
                prefix = getattr(obj, 'prefix', '')
                if prefix == "crs" and fault_cond:
                    fault_text = getattr(obj, 'fault_text', '')
                    detail_parts.append(f"Неисправность (код): {fault_cond}\n{fmt_txt(fault_text)}")
                    
                # Взвод (только если есть код)
                set_code = getattr(obj, 'set_code', None)
                if set_code:
                    set_text = getattr(obj, 'set_text', '')
                    detail_parts.append(f"Условие взвода (код): {set_code}\n{fmt_txt(set_text)}")
                
                # Сброс (только если есть код)
                reset_code = getattr(obj, 'reset_code', None)
                if reset_code:
                    reset_text = getattr(obj, 'reset_text', '')
                    detail_parts.append(f"Условие сброса (код): {reset_code}\n{fmt_txt(reset_text)}")
                
                # Записываем итоговый "бутерброд", только если в нем что-то есть
                if detail_parts:
                    ws_doc.Cells(current_row + 1, 2).Value = "\n\n".join(detail_parts)
                    current_row += 2
                else:
                    current_row += 1
            else:
                current_row += 1

        logger("Данные успешно перенесены на лист 'Документ'.", "INFO")
        # --- КОНЕЦ БЛОКА ПЕРЕНОСА ДАННЫХ ---

        # 3. ЗАПУСК МАКРОСА
        macro_name = getattr(config_class, 'MACRO_FORMAT_DOC', "Format_Document_Simple")
        
        # Читаем реальные настройки пользователя
        user_settings = load_settings()
        addon_path = user_settings.get('addon_path', AppConfig.ADD_ON) 
        
        addon_filename = os.path.basename(addon_path)

        filename = os.path.basename(filepath)
        logger(f"⚙️ Запуск макроса для обновления документа в конфигураторе {filename}...", "INFO")
        
        try:
            # ЖЕЛЕЗОБЕТОННО: Проверяем, загружена ли надстройка в текущий процесс Excel. Если нет - открываем её принудительно
            addon_loaded = False
            
            # 1. Сначала ищем среди просто открытых файлов (Workbooks)
            for opened_wb in excel.Workbooks:
                if opened_wb.Name.lower() == addon_filename.lower():
                    addon_loaded = True
                    break
            
            # 2. Затем ищем среди официально установленных в Excel надстроек (AddIns)
            if not addon_loaded:
                try:
                    for addin in excel.AddIns:
                        # Проверяем по имени и смотрим, активна ли она (Installed)
                        if addin.Name.lower() == addon_filename.lower() and addin.Installed:
                            addon_loaded = True
                            break
                except Exception:
                    pass
            
            # 3. И только если её вообще нет в памяти, пытаемся открыть файл по пути
            abs_addon_path = os.path.abspath(addon_path)
            
            if not addon_loaded:
                if os.path.exists(abs_addon_path):
                    excel.Workbooks.Open(abs_addon_path)
                else:
                    logger(f"⚠️ Файл надстройки не найден по пути: {abs_addon_path}, но попробуем выполнить из кэша...", "WARNING")

            # ЖЕЛЕЗОБЕТОННО: передаем Excel полный абсолютный путь к надстройке, чтобы он не искал ее в "Документах"
            full_macro_path = f"'{abs_addon_path}'!{macro_name}"
            
            excel.Run(full_macro_path)
            logger("Макрос успешно выполнен!", "INFO")
        except Exception as macro_e:
            logger(f"❌ Не удалось выполнить макрос {macro_name} из {addon_filename}: {str(macro_e)}", "WARNING")
        
        # Возвращаем обновление экрана и сохраняем файл
        if is_background:
            wb.Save()
            wb.Close()
            excel.Quit()
            logger(f"💾 Фоновый процесс завершен, {filename} сохранен.", "INFO")
        else:
            try:
                excel.ScreenUpdating = True
            except:
                pass
            wb.Save()
            
        return True

    except Exception as e:
        logger(f"❌ Ошибка при сборке Документа: {str(e)}", "ERROR")
        try:
            if 'is_background' in locals() and is_background and 'excel' in locals():
                excel.Quit()
            elif 'excel' in locals() and not is_background:
                excel.ScreenUpdating = True
        except:
            pass
        return False
    finally:
        pythoncom.CoUninitialize()