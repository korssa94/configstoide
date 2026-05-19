# parsers/base_parser.py
import datetime
import os

class BaseParser:
    def __init__(self, filepath, base_dir, matched_ctrls, config, logger=None):
        self.filepath = filepath
        self.base_dir = base_dir
        self.matched_ctrls = matched_ctrls
        self.config = config
        self.logger = logger
        self.objects = {} 
        self.errors = []
        self.files_to_write = []
        self.file_author = "Unknown"
        self.file_save_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def log(self, message, level="INFO"):
        if self.logger:
            self.logger(message, level)

    def get_column_mapping(self, ws, header_row):
        mapping = {}
        for col_idx in range(1, ws.max_column + 1):
            cell_val = ws.cell(row=header_row, column=col_idx).value
            if cell_val:
                clean_name = " ".join(str(cell_val).replace('\n', ' ').split()).lower()
                mapping[clean_name] = col_idx
        return mapping

    def find_col_idx(self, col_map, aliases):
        if isinstance(aliases, str): return col_map.get(aliases.lower())
        for alias in aliases:
            if alias.lower() in col_map: return col_map[alias.lower()]
        return None

    def generate_header(self, algo_folder, file_author, file_save_time, excel_version, description=""):
        macro_version = f"v{self.config.APP_VERSION}"
        header = (
            f"//++++++< Content:Path >++++++++++++++++++++++++++++++++++++++++++++++++++++++//\n"
            f"//{algo_folder}\n"
            f"//++++++< Content:Declaration >+++++++++++++++++++++++++++++++++++++++++++++++//\n"
            f"{{region INFO}}\n"
            f"(*\n"
            f" Назначение: {description}\n"
            f" Автор:   /{file_author}/ {file_save_time}\n"
            f" Версия:  {excel_version}\n"
            f" Макросы: {macro_version}\n"
            f"*)\n"
            f"{{endregion}}\n"
        )
        return header

    def generate_subsystems_gvl(self, valid_subsystems, source_name):
        """Создает файл subsystem.gvl в папке Глобальные переменные."""
        if not valid_subsystems:
            self.log("Необходимо создать список подсистем (пустой список)", level="ERROR")
            return

        global_folder = "00_Глобальные переменные"
        
        # Генерируем шапку
        h_txt = (
            f"//++++++< Content:Path >++++++++++++++++++++++++++++++++++++++++++++++++++++++//\n"
            f"//{global_folder}\n"
            f"//++++++< Content:Declaration >+++++++++++++++++++++++++++++++++++++++++++++++//\n"
            f"{{region INFO}}\n"
            f"(*\n"
            f" Назначение: Статусы подсистем\n"
            f" Автор:   /{self.file_author}/ {self.file_save_time}\n"
            f" Создано из конфигуратора {source_name}\n"
            f"*)\n"
            f"{{endregion}}\n"
            f"{{attribute 'qualified_only'}}\n"
            f"{{attribute 'symbol' := 'read'}}\n"
            f"VAR_GLOBAL\n"
        )

        for sub_str in valid_subsystems:
            # Парсим строку "Имя - Код - Номер", которую мы собрали в ТЭ5
            parts = [p.strip() for p in sub_str.split(" - ")]
            if len(parts) >= 3:
                name, code, num = parts[0], parts[1], parts[2]
                h_txt += f"\t{code} : Tsubsystem := (number := {num}); //Подсистема: {name}/№{num}\n"

        h_txt += "END_VAR\n"

        # Добавляем файл в очередь на запись для каждого контроллера
        for ctrl in self.matched_ctrls:
            # Путь: root / source / ПЛК / 00_Глобальные переменные / subsystem.gvl
            target_path = os.path.join(self.base_dir, self.config.SOURCE_FOLDER, ctrl, global_folder, "subsystem.gvl")
            self.files_to_write.append({"path": target_path, "text": h_txt})