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