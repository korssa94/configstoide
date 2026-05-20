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


def find_master_and_targets(current_dir, config_registry, master_keyword):
    """Поднимается по дереву до папки Config(s), ищет Мастер-конфигуратор
    и обходит current_dir в поисках всех целевых файлов (по KEYWORD_FILE из реестра).

    Возвращает кортеж:
        target_files (list[str]) — пути к найденным конфигураторам
        master_file (str | None) — путь к Мастер-конфигуратору
        project_root (str | None) — найденная папка Config/Configs
        final_root (str)          — рабочий корень: project_root → папка мастера → current_dir
    """
    target_files = []
    master_file = None
    project_root = None
    check_dir = current_dir

    while True:
        folder_name = os.path.basename(check_dir).lower()
        potential_masters = [
            os.path.join(check_dir, f) for f in os.listdir(check_dir)
            if master_keyword in f
            and f.endswith(('.xlsx', '.xlsm'))
            and not f.startswith('~$')
        ]
        if potential_masters and master_file is None:
            master_file = potential_masters[0]
        if folder_name in ["config", "configs"]:
            project_root = check_dir
            break
        parent = os.path.dirname(check_dir)
        if parent == check_dir:
            break
        check_dir = parent

    final_root = project_root if project_root else (
        os.path.dirname(master_file) if master_file else current_dir
    )

    active_keywords = []
    for v in config_registry.values():
        kw = v["config"].KEYWORD_FILE
        if isinstance(kw, list):
            active_keywords.extend(kw)
        else:
            active_keywords.append(kw)

    for root, dirs, files in os.walk(current_dir):
        for f in files:
            if f.startswith('~$') or not f.endswith(('.xlsx', '.xlsm')):
                continue
            if any(k in f for k in active_keywords):
                target_files.append(os.path.join(root, f))

    return target_files, master_file, project_root, final_root