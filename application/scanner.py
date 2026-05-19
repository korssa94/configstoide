import os
from application.settings.app_config import AppConfig
import pandas as pd

def find_plcopen_xmls(project_path):
    """Поиск всех самых больших .plcopen.xml в различных папках source.export на глубине 1"""
    xml_files = []
    debug_log = []
    
    parent_dir = os.path.dirname(project_path)
    debug_log.append(f"Корень проекта для поиска: {parent_dir}")
    
    if not os.path.exists(parent_dir):
        return [], ["❌ Корень проекта не найден"]

    for item in os.listdir(parent_dir):
        subdir_path = os.path.join(parent_dir, item)
        
        if os.path.isdir(subdir_path):
            export_dir = os.path.join(subdir_path, AppConfig.SOURCE_EXPORT_FOLDER)
            if os.path.exists(export_dir) and os.path.isdir(export_dir):
                debug_log.append(f"🔎 Найдена папка экспорта в: {item}")
                
                local_xmls = []
                try:
                    for f in os.listdir(export_dir):
                        full_path = os.path.join(export_dir, f)
                        if os.path.isfile(full_path) and f.lower().endswith(".plcopen.xml"):
                            local_xmls.append({
                                "path": full_path, 
                                "name": f, 
                                "size": os.path.getsize(full_path),
                                "module": item
                            })
                except Exception as e:
                    debug_log.append(f"  ❌ Ошибка чтения в {item}: {e}")
                    continue

                if local_xmls:
                    local_xmls.sort(key=lambda x: x['size'], reverse=True)
                    winner = local_xmls[0]
                    xml_files.append(winner)
                    debug_log.append(f"  ✅ Взят файл: {winner['name']} ({winner['size']//1024} KB)")

    return sorted(xml_files, key=lambda x: x['size'], reverse=True), debug_log

def cache_to_df(cache):
    """Преобразует вложенный словарь кэша в плоскую таблицу"""
    rows = []
    if not cache:
        return pd.DataFrame()
    for gvl, vars_dict in cache.items():
        for var, info in vars_dict.items():
            rows.append({
                    "GVL": info.get('orig_gvl', gvl),
                    "Переменная": info.get('orig_var', var),
                    "Тип": info.get('type', ''),
                    "Описание": info.get('comment', '')
                })
    return pd.DataFrame(rows)
