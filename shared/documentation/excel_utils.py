import zipfile
import os
import shutil
import re
import tempfile
import openpyxl
import xlwings as xw
from contextlib import contextmanager

def repair_and_cleanup_file(filepath, logger):
    """
    Ультимативная очистка. Распаковывает Excel как ZIP-архив и выжигает 
    конфликтующие имена прямо из исходного кода XML. 
    Блокирует любые попытки openpyxl или Excel скрыть от нас системные имена.
    """
    temp_dir = tempfile.mkdtemp()
    try:
        # 1. Распаковываем xlsm как обычный zip
        with zipfile.ZipFile(filepath, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        workbook_xml_path = os.path.join(temp_dir, 'xl', 'workbook.xml')
        
        # Если файла нет (что вряд ли), выходим
        if not os.path.exists(workbook_xml_path):
            return
        
        # 2. Читаем сырой XML
        with open(workbook_xml_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        # 3. Регулярное выражение, которое ищет теги <definedName ...> ... </definedName>
        # Ищет любые вхождения Print_Area, Print_Titles, Область_печати и т.д.
        pattern = re.compile(
            r'<definedName[^>]*name="[^"]*(Print_Area|Print_Titles|Область_печати|Заголовки_для_печати)[^"]*"[^>]*>.*?</definedName>',
            re.IGNORECASE | re.DOTALL
        )
        
        # Удаляем найденные теги из текста
        new_xml_content, count = pattern.subn('', xml_content)
        
        if count > 0:
            # 4. Перезаписываем XML без мусора
            with open(workbook_xml_path, 'w', encoding='utf-8') as f:
                f.write(new_xml_content)
            
            # 5. Собираем архив обратно
            temp_zip_path = filepath + '.tmp'
            with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as new_zip:
                for foldername, subfolders, filenames in os.walk(temp_dir):
                    for filename in filenames:
                        f_path = os.path.join(foldername, filename)
                        arcname = os.path.relpath(f_path, temp_dir)
                        new_zip.write(f_path, arcname)
            
            # Подменяем исходный файл вылеченным
            shutil.move(temp_zip_path, filepath)
            logger(f"🔥 ВЫЖЖЕНО ИЗ XML: {count} битых имен! Файл полностью очищен.", "INFO")
        else:
            logger("В XML-структуре мусорных имен не найдено.", "INFO")
            
    except Exception as e:
        logger(f"Ошибка при жесткой XML-очистке: {e}", "ERROR")
    finally:
        # Убираем за собой временную папку
        shutil.rmtree(temp_dir, ignore_errors=True)

def fix_print_settings(file_path, logger):
    """
    Аккуратное переименование Print_Area в Область_печати (для ТЭ5).
    Сохраняет координаты перед переименованием, чтобы не потерять настройки!
    """
    app = None
    try:
        app = xw.App(visible=False, add_book=False)
        wb = app.books.open(file_path)
        
        mapping = {
            "Print_Area": "Область_печати",
            "Print_Titles": "Заголовки_для_печати"
        }
        
        # Собираем список имен для перевода
        names_to_process = [n for n in list(wb.names) if any(k in n.name for k in mapping.keys())]
        
        for name in names_to_process:
            old_name = name.name 
            ref_range = name.refers_to # СНАЧАЛА СОХРАНЯЕМ КООРДИНАТЫ (Например: ='Вх.А сигн.'!$A$1:$P$214)
            
            new_name = old_name
            for eng, rus in mapping.items():
                if eng in old_name:
                    new_name = old_name.replace(eng, rus)
            
            name.delete() # Удаляем старое английское имя
            wb.names.add(new_name, refers_to=ref_range) # Восстанавливаем с русским именем по сохраненным координатам
        
        # Даем Excel команду перечитать области, чтобы они отобразились в интерфейсе
        for sheet in wb.sheets:
            try:
                area = sheet.api.PageSetup.PrintArea
                if area:
                    sheet.api.PageSetup.PrintArea = area
            except Exception:
                pass
        
        wb.save()
        wb.close()
        logger("[ExcelUtils] Настройки печати успешно пересозданы.", "INFO")
        
    except Exception as e:
        logger(f"[ExcelUtils] Ошибка при работе через xlwings: {e}", "ERROR")
        if 'wb' in locals(): wb.close()
    finally:
        if app:
            app.quit()

@contextmanager
def seamless_excel(filepath, logger, print_area_mode=None):
    """Универсальный контекст: открыть (или найти) книгу, заморозить экран,
    восстановить фокус после работы, сохранить, закрыть если сами открыли.

    print_area_mode (срабатывает ТОЛЬКО при фоновом открытии):
        None    — не трогать области печати
        "wipe"  — выжечь Print_Area/Print_Titles из XML ДО открытия
                  (для конфигураторов, где область печати создаётся макросом, например ТБ51)
        "fix"   — переименовать Print_Area → Область_печати ПОСЛЕ закрытия
                  (для конфигураторов с готовыми областями печати, например ТЭ5)
    """
    app = None
    wb = None
    original_wb_name = None
    is_background = False

    try:
        filename = os.path.basename(filepath)
        try:
            wb = xw.books[filename]
            app = wb.app
        except Exception:
            app = xw.App(visible=False)
            wb = None
            is_background = True

        # Запоминаем активную книгу и замораживаем экран ДО любых Activate
        try:
            original_wb_name = app.api.ActiveWorkbook.Name
            app.screen_updating = False
        except Exception:
            pass

        if wb is None:  # файл не был открыт — открываем (выжигаем XML, если попросили)
            if print_area_mode == "wipe":
                repair_and_cleanup_file(filepath, logger)
            wb = app.books.open(filepath)
            logger(f"📁 Открыли {filename} в фоновом режиме", "INFO")
        else:
            logger(f"🔗 Подключились к уже открытому {filename}", "INFO")

        yield app, wb, is_background

        wb.save()

    finally:
        if app:
            # Возвращаем фокус на исходную книгу, пока экран ещё заморожен
            if original_wb_name:
                try:
                    app.books[original_wb_name].activate()
                except Exception:
                    pass
            try:
                app.screen_updating = True
            except Exception:
                pass
            if is_background:
                try:
                    wb.close()
                except Exception:
                    pass
                try:
                    app.quit()
                except Exception:
                    pass
                logger(f"💾 Фоновый процесс завершён, {os.path.basename(filepath)} сохранён.", "INFO")

                # Аккуратное переименование Print_Area → Область_печати после закрытия
                if print_area_mode == "fix":
                    fix_print_settings(filepath, logger)
