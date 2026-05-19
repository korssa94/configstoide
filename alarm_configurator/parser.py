# parsers/alarm_parser.py
import openpyxl
import os
import re
import streamlit as st
import datetime
from shared.parsers.base_parser import BaseParser
from alarm_configurator.models.talr import Talr
from alarm_configurator.models.tppu import Tppu
from alarm_configurator.models.tcrs import Tcrs
from inout_configurator.config import TE5Config 
from application.settings.app_config import AppConfig

class AlarmParser(BaseParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def parse(self, clean_name, active_rules, te5_objects=None, skip_paint=False, force=False):
        try:
            wb_data = openpyxl.load_workbook(self.filepath, data_only=True)
            self.file_author = wb_data.properties.lastModifiedBy or "Unknown"
            if wb_data.properties.modified:
                utc_time = wb_data.properties.modified
                local_time = utc_time.replace(tzinfo=datetime.timezone.utc).astimezone(None)
                self.file_save_time = local_time.strftime("%Y-%m-%d %H:%M:%S")
            
            algo_folder = self.config.DEFAULT_ALGO_FOLDER

            # --- 1. СБОР ПОДСИСТЕМ (в методе parse) ---
            subsystems_map = {}
            if self.config.SHEET_SETTINGS in wb_data.sheetnames:
                ws_settings = wb_data[self.config.SHEET_SETTINGS]
                # Предположим, что структура: Название(0), Код(1), Номер(2)
                # Начинаем читать после заголовка "Подсистемы"
                start_reading = False
                for row in ws_settings.iter_rows(values_only=True):
                    if not row or not row[0]: continue
                    if "Подсистемы" in str(row[0]):
                        start_reading = True
                        continue
                    if start_reading:
                        name = str(row[0]).strip()
                        code = str(row[1]).strip()
                        num = str(row[2]).strip()
                        if code:
                            subsystems_map[code] = {"num": num, "name": name}
                            
                self.subsystems_map = subsystems_map # Запоминаем подсистемы в классе для шага генерации GVL

            # --- 2. ПАРСИНГ СИГНАЛИЗАЦИЙ ---
            all_parsed_objects = []
            current_sub_code = "" # Переменная-память

            if self.config.SHEET_ALARMS not in wb_data.sheetnames:
                self.log(f'Лист "{self.config.SHEET_ALARMS}" не найден.', level="ERROR")
                return False
            
            ws_data = wb_data[self.config.SHEET_ALARMS]
            col_map = self.get_column_mapping(ws_data, self.config.HEADER_ROW)

            # Подготавливаем словари для объектов (alr, trs, lmt и т.д.)
            for key in self.config.MODEL_SETTINGS.keys():
                self.objects[key] = []

            for row in range(self.config.DATA_START_ROW, ws_data.max_row + 1):
                def get_val(col_name):
                    idx = self.find_col_idx(col_map, col_name)
                    val = ws_data.cell(row=row, column=idx).value if idx else ""
                    return val if val is not None else ""
                
                type_str = str(get_val(self.config.COL_TYPE)).strip()
                msg = str(get_val(self.config.COL_MESSAGE)).strip()
                action = str(get_val(self.config.COL_ACTION)).strip()

                # ПРОВЕРКА: Это строка подсистемы? (VBA: Сообщение <> "" And Тип = "")
                if msg != "" and type_str == "":
                    # Алгоритмическое имя подсистемы в этой строке
                    current_sub_code = str(get_val(self.config.COL_ALG_NAME)).strip()
                    continue

                # 1. Анализируем строку (как в VBA)
                target_prefixes = []

                if type_str == "ПС":
                    if action in ["ХР", "ГР", "БЗ"]:
                        target_prefixes = ["alr", "ppu"]
                    else:
                        target_prefixes = ["alr"]
                
                elif type_str == "ППУ":
                    target_prefixes = ["ppu"]

                elif type_str == "АС":
                    if action not in ["АОсс", "АОбс", "ВОсс", "ВОбс", "АО", "ВО", "Пожар"]:
                        target_prefixes = ["trs"] # Тревожная
                    else:
                        target_prefixes = ["crs"] # Аварийная
                elif type_str == "ОС":
                    target_prefixes = ["lmt"] # Ограничительная

                # 2. Генерируем объекты по списку целей
                for prefix in target_prefixes:
                    if prefix in ["alr", "trs", "lmt"]:
                        obj = Talr(row, get_val, self.config, prefix=prefix)
                    elif prefix == "ppu":
                        obj = Tppu(row, get_val, self.config, prefix=prefix)
                    elif prefix == "crs":
                        obj = Tcrs(row, get_val, self.config, prefix=prefix)
                    else:
                        continue
                    
                    # Присваиваем данные подсистемы из памяти
                    sub_info = subsystems_map.get(current_sub_code, {})
                    obj.subsystem_code = current_sub_code
                    obj.subsystem_num = sub_info.get("num", "")
                    obj.subsystem_name = sub_info.get("name", "")

                    # Раскладываем по нужным спискам
                    all_parsed_objects.append(obj)
                    if obj.prefix in self.objects:
                        self.objects[obj.prefix].append(obj)

            # Сохраняем книгу и плоский список объектов внутри класса
            self.wb_data = wb_data 
            self.all_parsed_objects = all_parsed_objects

            # Запоминаем начальное количество сигналов по типам для статистики
            initial_counts = {prefix: len(items) for prefix, items in self.objects.items()}

            # --- 1. ПЕРВИЧНЫЙ АНАЛИЗ (Выводим ТОЛЬКО при первом запуске) ---
            if not force:
                for prefix, initial_cnt in initial_counts.items():
                    if initial_cnt > 0:
                        self.log(f'Собрано {initial_cnt} сигналов типа "{prefix}".', level="INFO")

            # --- 2. КРОСС-ПРОВЕРКА С ТЭ5 ---
            is_valid = self._cross_validate(self.filepath, all_parsed_objects, clean_name, force=force)
            
            if not is_valid and not force:
                self.log("❌ Обнаружены ошибки кросс-проверки. Процесс остановлен.", level="ERROR")
                return False

            # --- 3. ФИНАЛЬНЫЕ ИТОГИ ГЕНЕРАЦИИ (Выводим ТОЛЬКО при force=True) ---
            if force:
                for prefix, initial_cnt in initial_counts.items():
                    current_cnt = len(self.objects.get(prefix, []))
                    skipped_cnt = initial_cnt - current_cnt
                    
                    if skipped_cnt > 0:
                        self.log(f'Тип "{prefix}": создано {current_cnt} сигналов, пропущено {skipped_cnt} из-за ошибок кросс-проверки.', level="INFO")
                    else:
                        if current_cnt > 0:
                            self.log(f'Тип "{prefix}": создано {current_cnt} сигналов.', level="INFO")

            # --- 4. ГЕНЕРАЦИЯ ФАЙЛОВ ---
            self._generate_files(algo_folder, self.all_parsed_objects)
            
            return True

        except Exception as e:
            self.log(f"Ошибка в парсере Сигнализаций: {str(e)}", level="ERROR")
            return False

    def _generate_files(self, algo_folder, all_parsed_objects):
        fn = os.path.basename(self.filepath)
        excel_v = (re.search(r'v\d+\.\d+\.\d+', fn).group(0) if re.search(r'v\d+\.\d+\.\d+', fn) else "none")
        
        st_grouped = {} # Для группировки ST файлов { "alr_update.st": { "desc": "...", "content": "...", "global_var": "alr" } }

        # ШАГ 1: ГЕНЕРАЦИЯ GVL (Индивидуально для каждого префикса)
        for prefix, settings in self.config.MODEL_SETTINGS.items():
            prefix_objects = self.objects.get(prefix, [])
            
            # 1. Системная шапка (создается всегда)
            gvl_txt = self.generate_header(algo_folder, self.file_author, self.file_save_time, excel_v, settings.get("desc_gvl", ""))
            
            # 2. Декларативная шапка ТИПА
            if prefix_objects:
                # Если объекты есть, берем специфичную шапку у первого (например, для ППУ)
                gvl_txt += prefix_objects[0].get_gvl_header()
            else:
                # Если объектов нет, выводим базовую структуру (как в твоем примере ОС)
                gvl_txt += "{attribute 'qualified_only'}\n"
                gvl_txt += "{attribute 'symbol' := 'read'}\n"
                gvl_txt += "VAR_GLOBAL\n"
                gvl_txt += "\t{attribute 'symbol' := 'none'}\n"
                gvl_txt += "\tcommon : Talarm; //Общий сигнал для VAR_STAT\n\n"

            # 3. Сами сигналы (только если они есть)
            if prefix_objects:
                gvl_txt += "\n".join([o.get_gvl_string() for o in prefix_objects]) + "\n"
            
            gvl_txt += "END_VAR\n"
            
            for ctrl in self.matched_ctrls:
                tdir = os.path.join(self.base_dir, self.config.SOURCE_FOLDER, ctrl, algo_folder)
                self.files_to_write.append({"path": os.path.join(tdir, settings["file_gvl"]), "text": gvl_txt})


        # ШАГ 2: ГЕНЕРАЦИЯ ST (Собираем все префиксы в общие ST-файлы по порядку)
        st_grouped = {}
        
        # all_parsed_objects - это список всех объектов строго в порядке строк из Excel
        for obj in all_parsed_objects: 
            # Узнаем, в какой ST-файл должен идти этот объект (например, alr_update.st)
            settings = self.config.MODEL_SETTINGS.get(obj.prefix, {})
            f_st = settings.get("file_st")
            
            if not f_st:
                continue # Если файл ST не указан, пропускаем
                
            # Инициализируем хранилище для файла, если его еще нет
            if f_st not in st_grouped:
                st_grouped[f_st] = {
                    "desc": settings.get("desc_st", ""), 
                    "global_var": settings.get("global_var", "alr"), 
                    "content": "",
                    "last_subsystem": None # Память для заголовков подсистем ВНУТРИ файла
                }
            elif settings.get("desc_st"):
                st_grouped[f_st]["desc"] = settings["desc_st"]
                st_grouped[f_st]["global_var"] = settings["global_var"]

            # Логика отрисовки красивых заголовков подсистем
            if obj.subsystem_name != st_grouped[f_st]["last_subsystem"]:
                if st_grouped[f_st]["content"] == "":
                        st_grouped[f_st]["content"] += "//==========================================================================\n\n"
                st_grouped[f_st]["content"] += "//==========================================================================\n"
                st_grouped[f_st]["content"] += f"//Подсистема: {obj.subsystem_name}\n"
                st_grouped[f_st]["content"] += "//==========================================================================\n"
                st_grouped[f_st]["last_subsystem"] = obj.subsystem_name
            
            # Добавляем вызов самого блока
            st_grouped[f_st]["content"] += obj.get_st_string() + "\n"

        # ШАГ 3: Сохраняем сгруппированные ST файлы
        for f_st, data in st_grouped.items():
            h_st = self.generate_header(algo_folder, self.file_author, self.file_save_time, excel_v, data["desc"])
            st_txt = h_st + f"FUNCTION {data['global_var']}_update : BOOL\nVAR_INPUT\nEND_VAR\n"
            st_txt += "//++++++< Content:Implementation >++++++++++++++++++++++++++++++++++++++++++++//\n"
            st_txt += data["content"]
            
            for ctrl in self.matched_ctrls:
                tdir = os.path.join(self.base_dir, self.config.SOURCE_FOLDER, ctrl, algo_folder)
                self.files_to_write.append({"path": os.path.join(tdir, f_st), "text": st_txt})

        # --- ШАГ 4: ГЕНЕРАЦИЯ ФАЙЛА СБРОСА reset_alarm_var_stat.st ---
        reset_txt = (
            f"//++++++< Content:Path >++++++++++++++++++++++++++++++++++++++++++++++++++++++//\n"
            f"//{algo_folder}\n"
            f"//++++++< Content:Declaration >+++++++++++++++++++++++++++++++++++++++++++++++//\n"
            f"{{region INFO}}\n"
            f"(*\n"
            f" Назначение: Используется для сброса всех VAR_STAT сигнализаций\n"
            f" Автор:   /{self.file_author}/ {self.file_save_time}\n"
            f" Версия:  {excel_v}\n"
            f" Макросы: v1.0.0\n"
            f"*)\n"
            f"{{endregion}}\n"
            f"FUNCTION reset_alarm_var_stat : BOOL\n"
            f"VAR_INPUT\n"
            f"END_VAR\n"
            f"//++++++< Content:Implementation >++++++++++++++++++++++++++++++++++++++++++++//\n"
            f"//Сбрасываем обобщенные сигнализации\n"
            f"//По типу и подсистемам в 0, потому что при сработке они выставляются в 1\n"
            f"crs.common.type_aggregated := crs.common.subsystem_aggregated := 0;\n"
            f"//По взводу защит все биты в 1, потому что при отсутствии взвода они сбрасываются в 0\n"
            f"crs.common.arm_aggregated := 16#FFFFFFFF;\n"
            f"//По типу биты 1-3 в 0 (для alr, lmt и trs, потому что при сработке они выставляются в 1), 4 и 5 в 1 (для ppu, потому что при сработке они сбрасываются в 0)\n"
            f"alr.common.type_aggregated := 2#1110000;\n"
            f"//Для типов alr, lmt и trs по подсистемам все биты в 0, потому что при сработке они выставляются в 1\n"
            f"alr.common.subsystem_aggregated[1] := alr.common.subsystem_aggregated[2] := alr.common.subsystem_aggregated[3] := 0;\n"
            f"//Для ППУ по подсистемам все биты в 1, потому что при сработке они сбрасываются в 0\n"
            f"alr.common.subsystem_aggregated[4] := alr.common.subsystem_aggregated[5] := 16#FFFFFFFF;\n"
        )
        
        for ctrl in self.matched_ctrls:
            tdir = os.path.join(self.base_dir, self.config.SOURCE_FOLDER, ctrl, algo_folder)
            self.files_to_write.append({"path": os.path.join(tdir, "reset_alarm_var_stat.st"), "text": reset_txt})

        # --- ШАГ 5: ГЕНЕРАЦИЯ subsystem.gvl ДЛЯ ВСЕХ КОНТРОЛЛЕРОВ ---
        sub_list = [f"{info['name']} - {code} - {info['num']}" for code, info in getattr(self, 'subsystems_map', {}).items()]
        self.generate_subsystems_gvl(sub_list, "сигнализаций")
            
        return True

    def _cross_validate(self, filepath, alarms_objects, clean_name, force=False):
        """
        ВРЕМЕННАЯ ВЕРСИЯ ДЛЯ ДЕБАГА: 
        Двойное быстрое чтение: Мастер-конфигуратор -> связанные ТЭ5.
        """
        # --- БЛИЦ-ВЫХОД ДЛЯ ПОВТОРНОГО ЗАПУСКА (FORCE MODE) ---
        # Если этот файл уже проверялся и в сессии лежит готовый кэш дефектных строк
        if force and hasattr(st, 'session_state') and 'failed_rows_cache' in st.session_state:
            failed_rows = st.session_state.failed_rows_cache.get(clean_name, set())
            if failed_rows:
                ws_alarms = self.wb_data[self.config.SHEET_ALARMS]
                col_map = self.get_column_mapping(ws_alarms, self.config.HEADER_ROW)
                col_param_code = getattr(self.config, "COL_PARAM_CODE", "Алг.имя сигнала")
                
                def get_cell_val(row_idx, col_name):
                    idx = self.find_col_idx(col_map, col_name)
                    val = ws_alarms.cell(row=row_idx, column=idx).value if idx else ""
                    return str(val).strip() if val is not None else ""

                # Молча пишем лаконичные предупреждения и вырезаем дефектные объекты
                for r in sorted(list(failed_rows)):
                    p_name = get_cell_val(r, col_param_code)
                    p_desc = get_cell_val(r, self.config.COL_MESSAGE)
                    self.log(f"⚠️ Переменная со строки {r}, наименованием '{p_desc or '---'}', алг. именем '{p_name or '---'}' исключена из генерации (провал кросс-проверки)", level="WARNING")

                get_obj_row = lambda o: getattr(o, 'row_number', getattr(o, 'row', None))
                self.all_parsed_objects = [obj for obj in self.all_parsed_objects if get_obj_row(obj) not in failed_rows]
                for prefix in self.objects.keys():
                    self.objects[prefix] = [obj for obj in self.objects[prefix] if get_obj_row(obj) not in failed_rows]
            return True

        # --- ОСНОВНОЙ ПЕРВЫЙ ПРОХОД (РЕЖИМ АНАЛИЗА) ---
        tb51_filename = os.path.basename(filepath)
        self.log(f"🚀 Старт кросс-проверки (сбор данных) для {clean_name}", level="INFO")

        master_path = getattr(self, 'master_file', None)
        
        if not master_path or not os.path.exists(master_path):
            self.log("⚠️ Путь к Мастер-конфигуратору не передан или файл не найден. Кросс-проверка пропущена.", level="WARNING")
            return True

        self.log("📂 Чтение карты связей из Мастер-конфигуратора...", level="INFO")
        linked_te5_files = []
        try:
            wb_master = openpyxl.load_workbook(master_path, data_only=True, read_only=True)
            ws_master = wb_master.active 
            
            rows = list(ws_master.iter_rows(min_row=1, max_row=50, values_only=True))

            row_ctrl = next((i for i, r in enumerate(rows) if r[0] and AppConfig.MASTER_ROW_CTRL  in str(r[0]).lower()), None)
            row_te5  = next((i for i, r in enumerate(rows) if r[0] and AppConfig.MASTER_ROW_TE5   in str(r[0]).lower()), None)
            row_tb51 = next((i for i, r in enumerate(rows) if r[0] and AppConfig.MASTER_ROW_TB51  in str(r[0]).lower()), None)
            if None in (row_ctrl, row_te5, row_tb51):
                self.log("⚠️ Не найдены ключевые строки в Мастер-конфигураторе.", "WARNING")
                return True
            
            if row_ctrl is not None and row_te5 is not None and row_tb51 is not None:
                for col_idx in range(1, len(rows[row_ctrl])):
                    tb51_val = rows[row_tb51][col_idx]
                    
                    if tb51_val and (clean_name in str(tb51_val).strip() or str(tb51_val).strip() == tb51_filename):
                        ctrl = rows[row_ctrl][col_idx]
                        te5 = rows[row_te5][col_idx]
                        if ctrl and te5:
                            linked_te5_files.append({"controller": str(ctrl).strip(), "te5_file": str(te5).strip()})

            wb_master.close()
            self.log(f"🔗 Найдено связей: {len(linked_te5_files)}. Контроллеры: {[f['controller'] for f in linked_te5_files]}", level="INFO")

        except Exception as e:
            self.log(f"❌ Ошибка при чтении Мастер-конфигуратора: {e}", level="ERROR")
            return False

        if not linked_te5_files:
            self.log("⚠️ В Мастер-конфигураторе не найдено привязанных ТЭ5 для этого ТБ51.", level="WARNING")
            return True

        base_dir = os.path.dirname(filepath) 
        te5_signals = {} 
        ctrl_to_file = {} 
        
        # 1. Сначала группируем контроллеры по уникальным путям файлов ТЭ5
        te5_groups = {} # Структура: te5_path -> [список контроллеров]
        
        for link in linked_te5_files:
            ctrl_name = link['controller']
            te5_base_name = link['te5_file']
            te5_path = None
            if os.path.exists(base_dir):
                for f in os.listdir(base_dir):
                    if f.startswith(te5_base_name) and f.endswith(('.xlsm', '.xlsx')) and not f.startswith('~$'):
                        te5_path = os.path.join(base_dir, f)
                        break
            
            if not te5_path:
                self.log(f"⚠️ Файл для {te5_base_name} (контроллер {ctrl_name}) не найден в папке. Пропуск.", level="WARNING")
                continue

            ctrl_to_file[ctrl_name] = os.path.basename(te5_path)
            te5_groups.setdefault(te5_path, []).append(ctrl_name)

        # 2. Итерируемся по уникальным файлам (читаем каждый файл строго ОДИН раз)
        for te5_path, ctrls in te5_groups.items():
            fname = os.path.basename(te5_path)
            ctrls_str = ", ".join(ctrls)
            
            # Выводим одну красивую объединенную строку в лог
            self.log(f"📂 Быстрое чтение {fname} для ПЛК {ctrls_str}...", level="INFO")
            
            extracted_signals = [] 
            try:
                wb_te5 = openpyxl.load_workbook(te5_path, data_only=True, read_only=True)
                
                # Создаем карту соответствия русских заголовков из конфига и латинских кодов
                sp_header_map = {
                    TE5Config.COL_LL.lower().strip(): "ll",
                    TE5Config.COL_L1.lower().strip(): "l1",
                    TE5Config.COL_L.lower().strip(): "l",
                    TE5Config.COL_H.lower().strip(): "h",
                    TE5Config.COL_H1.lower().strip(): "h1",
                    TE5Config.COL_HH.lower().strip(): "hh"
                }

                for sig_type, settings in TE5Config.MODEL_SETTINGS.items():
                    sheet_name = settings.get("sheet_name")
                    if sheet_name in wb_te5.sheetnames:
                        ws_te5 = wb_te5[sheet_name]
                        alg_col_idx = None
                        create_col_idx = None
                        setpoint_cols = {}
                        
                        for row in ws_te5.iter_rows(min_row=TE5Config.HEADER_ROW, max_row=TE5Config.HEADER_ROW, values_only=True):
                            for col_idx, cell_val in enumerate(row):
                                if cell_val:
                                    header = str(cell_val).strip().lower()
                                    if header == TE5Config.COL_ALG_NAME.lower():
                                        alg_col_idx = col_idx
                                    elif header == TE5Config.COL_CREATE_CODE.lower():
                                        create_col_idx = col_idx
                                    elif header in sp_header_map:
                                        setpoint_cols[sp_header_map[header]] = col_idx
                            if alg_col_idx is not None and create_col_idx is not None: 
                                break

                        if alg_col_idx is not None and create_col_idx is not None:
                            for row in ws_te5.iter_rows(min_row=TE5Config.DATA_START_ROW, values_only=True):
                                all_indices = [alg_col_idx, create_col_idx] + list(setpoint_cols.values())
                                max_idx = max(all_indices) if all_indices else 0
                                
                                if len(row) > max_idx:
                                    alg_val = row[alg_col_idx]
                                    create_val = row[create_col_idx]
                                    
                                    if alg_val and str(alg_val).strip():
                                        alg_str = str(alg_val).strip()
                                        
                                        if str(create_val).strip() == "1" or create_val == 1:
                                            active_setpoints = []
                                            if sig_type.lower() == "taipar":
                                                for sp_name, sp_col in setpoint_cols.items():
                                                    sp_val = row[sp_col]
                                                    if sp_val is not None and str(sp_val).strip() != "":
                                                        active_setpoints.append(sp_name)
                                            
                                            extracted_signals.append((sig_type.lower(), alg_str, active_setpoints))
                wb_te5.close()
                
                # Раскидываем собранные сигналы сразу всем контроллерам этой группы
                for ctrl_name in ctrls:
                    te5_signals[ctrl_name] = extracted_signals
                    
            except Exception as e:
                self.log(f"❌ Ошибка при чтении {fname}: {e}", level="ERROR")

        self.log(f"⏱️ Сбор данных для проверки завершен", level="INFO")

        # === ЭТАП СРАВНЕНИЯ ДАННЫХ ===
        self.log("🔍 Запуск перекрестной проверки сигналов...", level="INFO")
        
        # Хэш-таблица множеств для мгновенного поиска O(1) в нижнем регистре (защита от случайных опечаток в регистре букв)
        te5_lookup = {}
        for ctrl, signals in te5_signals.items():
            # Теперь преобразуем в словарь, где ключ — (тип, имя), а значение — множество активных уставок
            te5_lookup[ctrl] = {}
            for item in signals:
                s_type = item[0].lower()
                s_name = item[1].lower()
                s_sps = set(item[2]) if len(item) > 2 else set()
                te5_lookup[ctrl][(s_type, s_name)] = s_sps

        ws_alarms = self.wb_data[self.config.SHEET_ALARMS]
        col_map = self.get_column_mapping(ws_alarms, self.config.HEADER_ROW)

        def get_cell_val(row_idx, col_name):
            idx = self.find_col_idx(col_map, col_name)
            val = ws_alarms.cell(row=row_idx, column=idx).value if idx else ""
            return str(val).strip() if val is not None else ""

        failed_rows = set()
        
        # Подтягиваем имена столбцов из конфигурации (с фоллбэками на стандартные имена, если в конфиге ТБ51 они названы иначе)
        col_cond_code = getattr(self.config, "COL_CONDITION_CODE", "Условие (код)")
        col_setpoint = getattr(self.config, "COL_SETPOINT", "Уставка")
        col_condition = getattr(self.config, "COL_CONDITION", "Условие")
        col_param_code = getattr(self.config, "COL_PARAM_CODE", "Алг.имя сигнала")

        # Идем напрямую по строкам листа сигнализаций Excel
        for r in range(self.config.DATA_START_ROW, ws_alarms.max_row + 1):
            
            cond_code = get_cell_val(r, col_cond_code)
            # 1. Проверяем только те сигнализации, для которых код создается автоматически (ячейка пуста)
            if cond_code != "":
                continue

            setpoint = get_cell_val(r, col_setpoint)
            condition = get_cell_val(r, col_condition)
            param_code = get_cell_val(r, col_param_code)

            # Если алгоритмическое имя пустое (например, пустая строка или строка подсистемы), пропускаем
            if not param_code or "резерв" in param_code.lower():
                continue

            expected_type = None
            
            # 2. Логика определения дискретного параметра
            if (setpoint == "" and condition == "DI") or setpoint == "N":
                expected_type = "tdipar"
            # 3. Логика определения аналогового параметра
            elif setpoint in ["LL", "L1", "L", "H", "H1", "HH"]:
                expected_type = "taipar"

            if expected_type:
                missing_param_ctrls = []
                missing_sp_ctrls = []
                
                # Сначала собираем списки отказавших контроллеров без вывода в лог
                for ctrl in te5_signals.keys():
                    lookup_dict = te5_lookup.get(ctrl, {})
                    key = (expected_type, param_code.lower())
                    
                    if key not in lookup_dict:
                        missing_param_ctrls.append(ctrl)
                    else:
                        if expected_type == "taipar":
                            sp_to_check = setpoint.lower()
                            if sp_to_check in ["ll", "l1", "l", "h", "h1", "hh"]:
                                active_sps = lookup_dict[key]
                                if sp_to_check not in active_sps:
                                    missing_sp_ctrls.append(ctrl)

                # А теперь группируем и выводим красиво по файлам ТЭ5
                if missing_param_ctrls:
                    file_groups = {}
                    for ctrl in missing_param_ctrls:
                        fname = ctrl_to_file.get(ctrl, "Неизвестный ТЭ5")
                        file_groups.setdefault(fname, []).append(ctrl)
                        
                    for fname, ctrls in file_groups.items():
                        failed_rows.add(r)
                        if not force:
                            fname_clean = os.path.splitext(fname)[0]
                            ctrls_str = ", ".join(ctrls)
                            err_msg = f"Строка {r}: [{fname_clean}, ПЛК {ctrls_str}] Сигнал '{param_code}' не найден в ТЭ5 как {expected_type}."
                            self.log(err_msg, level="ERROR")
                            if not hasattr(self, 'errors'): self.errors = []
                            self.errors.append(err_msg)

                if missing_sp_ctrls:
                    file_groups = {}
                    for ctrl in missing_sp_ctrls:
                        fname = ctrl_to_file.get(ctrl, "Неизвестный ТЭ5")
                        file_groups.setdefault(fname, []).append(ctrl)
                        
                    for fname, ctrls in file_groups.items():
                        failed_rows.add(r)
                        if not force:
                            fname_clean = os.path.splitext(fname)[0]
                            ctrls_str = ", ".join(ctrls)
                            err_msg = f"Строка {r}: [{fname_clean}, ПЛК {ctrls_str}] У параметра '{param_code}' в ТЭ5 не задана (пустая) уставка '{setpoint}'."
                            self.log(err_msg, level="ERROR")
                            if not hasattr(self, 'errors'): self.errors = []
                            self.errors.append(err_msg)

        # Сохраняем найденные дефектные строки в глобальный кэш сессии Streamlit
        if hasattr(st, 'session_state'):
            st.session_state.failed_rows_cache[clean_name] = failed_rows

        if failed_rows:
            self.log(f"❌ Перекрестная проверка завершена. Найдено ошибочных строк: {len(failed_rows)}", level="ERROR")
            return False
            
        self.log("✅ Перекрестная валидация ТБ51 и ТЭ5 успешно пройдена для всех контроллеров!", level="INFO")
        return True
    
