import zipfile
import os
import shutil
import re
import tempfile
import openpyxl
import xlwings as xw

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
    1. Если файл не открывается xlwings (ошибка Excel), чистим его через openpyxl.
    2. Если файл открылся, аккуратно пересоздаем области печати.
    """
    
    # --- ЭТАП 1: АВАРИЙНАЯ ОЧИСТКА (если файл поврежден) ---
    try:
        # Пробуем открыть файл "обычным" путем
        wb = openpyxl.load_workbook(file_path, keep_vba=True)
        # Ищем и удаляем мусорные имена, которые мешают Excel открыться
        names_to_delete = [n for n in wb.defined_names.keys() if 'Print_Area' in n or 'Print_Titles' in n]
        if names_to_delete:
            for name in names_to_delete:
                del wb.defined_names[name]
            wb.save(file_path)
            logger("[ExcelUtils] Файл был поврежден, очистили имена через openpyxl.", "INFO")
    except Exception as e:
        logger(f"[ExcelUtils] openpyxl не смог очистить файл (возможно, он не поврежден): {e}", "DEBUG")

    # --- ЭТАП 2: КОРРЕКТНАЯ НАСТРОЙКА (через xlwings) ---
    app = None
    try:
        app = xw.App(visible=False, add_book=False)
        wb = app.books.open(file_path)
        
        # Пересоздаем области печати "чисто"
        # Обязательно оборачиваем в list(), чтобы создать статичную копию
        # и не ломать динамические индексы Excel при удалении элементов
        for name in list(wb.names):
            try:
                if "Print_Area" in name.name or "Print_Titles" in name.name:
                    name.delete()
            except Exception:
                pass
        
        for sheet in wb.sheets:
            try:
                area = sheet.page_setup.print_area
                if area:
                    sheet.page_setup.print_area = area
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