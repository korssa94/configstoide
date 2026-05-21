import os
from application.settings.app_config import AppConfig
from application.settings_manager import load_settings
from shared.documentation.excel_utils import seamless_excel


def update_configurator_document(filepath, parsed_objects, config_class, logger):
    """Универсально заполняет лист 'Документ' данными и вызывает макрос форматирования из надстройки."""
    try:
        filename = os.path.basename(filepath)

        with seamless_excel(filepath, logger, print_area_mode="wipe") as (app, wb, is_background):
            # --- УНИВЕРСАЛЬНЫЕ НАСТРОЙКИ ---
            sheet_doc_name = getattr(config_class, 'SHEET_DOC', None)
            sheet_alarms_name = getattr(config_class, 'SHEET_ALARMS', None)
            sheet_internal_name = getattr(config_class, 'SHEET_INTERNAL', None)

            # Проверяем листы
            sheet_names = [sh.name for sh in wb.sheets]
            if sheet_doc_name not in sheet_names or not sheet_alarms_name or sheet_alarms_name not in sheet_names:
                logger(f"⚠️ Не найдены целевые листы в {filename}.", "WARNING")
                return

            ws_doc = wb.sheets[sheet_doc_name]
            ws_main = wb.sheets[sheet_alarms_name]
            ws_tr = wb.sheets[sheet_internal_name] if sheet_internal_name in sheet_names else None

            # --- ОЧИСТКА ЛИСТА ДОКУМЕНТ (со 2-й строки) ---
            last_row_doc = ws_doc.range((ws_doc.api.Rows.Count, 1)).end('up').row
            if last_row_doc > 1:
                ws_doc.range(f"2:{last_row_doc + 100}").clear()

            ws_doc.range("A:A").number_format = "@"

            current_row = 2

            # --- КОПИРОВАНИЕ ВНУТРЕННИХ СИГНАЛИЗАЦИЙ (без буфера обмена) ---
            if ws_tr:
                tr_last_row = ws_tr.range((ws_tr.api.Rows.Count, 1)).end('up').row
                if tr_last_row > 1:
                    tr_range_prefix = getattr(config_class, 'INTERNAL_COPY_RANGE', 'A2:K')
                    src_addr = f"{tr_range_prefix}{tr_last_row}"
                    ws_doc.range(src_addr).value = ws_tr.range(src_addr).value
                    current_row = tr_last_row + 1

            # --- ПЕРЕНОС ОСНОВНЫХ ДАННЫХ И ВСТАВКА ДЕТАЛЬНОГО ТЕКСТА ---
            obj_dict = {getattr(obj, 'row_number', i): obj for i, obj in enumerate(parsed_objects)}

            col_check = getattr(config_class, 'COL_DOC_CHECK', 5)
            main_last_row = ws_main.range((ws_main.api.Rows.Count, col_check)).end('up').row

            for i in range(2, main_last_row + 1):
                col_val = ws_main.cells(i, col_check).value
                if not col_val:
                    continue

                copy_range_str = getattr(config_class, 'DOC_COPY_RANGE', f"E{i}:O{i}")
                if "{i}" in copy_range_str:
                    copy_range_str = copy_range_str.format(i=i)

                ws_doc.range(f"A{current_row}:K{current_row}").value = ws_main.range(copy_range_str).value

                if i in obj_dict:
                    obj = obj_dict[i]
                    trigger_cond = getattr(obj, 'trigger_cond', None)

                    # Если кода нет — вообще ничего не пишем во вторую строку
                    if not trigger_cond:
                        current_row += 1
                        continue

                    def fmt_txt(val):
                        return str(val or "").replace("_x000D_", "").replace("\r", "").strip()

                    detail_parts = []

                    trigger_text = getattr(obj, 'trigger_text', '')
                    detail_parts.append(f"Условие (код): {trigger_cond}\n{fmt_txt(trigger_text)}")

                    fault_cond = getattr(obj, 'fault_cond', None)
                    prefix = getattr(obj, 'prefix', '')
                    if prefix == "crs" and fault_cond:
                        fault_text = getattr(obj, 'fault_text', '')
                        detail_parts.append(f"Неисправность (код): {fault_cond}\n{fmt_txt(fault_text)}")

                    set_code = getattr(obj, 'set_code', None)
                    if set_code:
                        set_text = getattr(obj, 'set_text', '')
                        detail_parts.append(f"Условие взвода (код): {set_code}\n{fmt_txt(set_text)}")

                    reset_code = getattr(obj, 'reset_code', None)
                    if reset_code:
                        reset_text = getattr(obj, 'reset_text', '')
                        detail_parts.append(f"Условие сброса (код): {reset_code}\n{fmt_txt(reset_text)}")

                    if detail_parts:
                        ws_doc.cells(current_row + 1, 2).value = "\n\n".join(detail_parts)
                        current_row += 2
                    else:
                        current_row += 1
                else:
                    current_row += 1

            logger("Данные успешно перенесены на лист 'Документ'.", "INFO")

            # --- ЗАПУСК МАКРОСА ИЗ НАДСТРОЙКИ ---
            macro_name = getattr(config_class, 'MACRO_FORMAT_DOC', "Format_Document_Simple")
            user_settings = load_settings()
            addon_path = user_settings.get('addon_path', AppConfig.ADD_ON)
            addon_filename = os.path.basename(addon_path)
            abs_addon_path = os.path.abspath(addon_path)

            logger(f"⚙️ Запуск макроса для обновления документа в конфигураторе {filename}...", "INFO")

            # Глушим Workbook_Open и алерты строго на время работы с надстройкой
            try:
                app.api.DisplayAlerts = False
                app.api.EnableEvents = False
            except Exception:
                pass

            try:
                # Проверяем, загружена ли надстройка в текущий процесс Excel
                addon_loaded = False

                # 1. Среди открытых книг (Workbooks)
                for opened_wb in app.books:
                    if opened_wb.name.lower() == addon_filename.lower():
                        addon_loaded = True
                        break

                # 2. Среди установленных надстроек (AddIns через .api)
                if not addon_loaded:
                    try:
                        for addin in app.api.AddIns:
                            if addin.Name.lower() == addon_filename.lower() and addin.Installed:
                                addon_loaded = True
                                break
                    except Exception:
                        pass

                # 3. Если в памяти нет — открываем физический файл
                if not addon_loaded:
                    if os.path.exists(abs_addon_path):
                        app.api.Workbooks.Open(abs_addon_path)
                    else:
                        logger(f"⚠️ Файл надстройки не найден: {abs_addon_path}, попробуем из кэша...", "WARNING")

                # Передаём Excel ПОЛНЫЙ путь, чтобы он не искал макрос в Документах
                full_macro_path = f"'{abs_addon_path}'!{macro_name}"

                # Макрос внутри обращается к ActiveWorkbook.Sheets("Документ"),
                # поэтому активируем нужную книгу строго перед запуском.
                wb.activate()

                app.api.Run(full_macro_path)
                logger("Макрос успешно выполнен!", "INFO")

            except Exception as macro_e:
                logger(f"❌ Не удалось выполнить макрос {macro_name} из {addon_filename}: {str(macro_e)}", "WARNING")
            finally:
                try:
                    app.api.DisplayAlerts = True
                    app.api.EnableEvents = True
                except Exception:
                    pass

    except Exception as e:
        logger(f"❌ Ошибка при сборке Документа: {str(e)}", "ERROR")