from settings import AppConfig

class TE5Config(AppConfig):
    """Настройки, специфичные ТОЛЬКО для конфигуратора ТЭ5"""
    KEYWORD_FILE = "ТЭ5"
    DEFAULT_ALGO_FOLDER = "04_Входы_выходы"
    # --- ПОДДЕРЖИВАЕМЫЕ ФУНКЦИИ ---
    SUPPORT_TEXT_UPDATE = False
    SUPPORT_DOC_UPDATE = False
    SUPPORT_COLOR_UPDATE = True

    # --- КАРТА ГЕНЕРАЦИИ ---
    MODEL_SETTINGS = {
        "Taipar": {
            "sheet_name": "Вх.А сигн.",
            "file_gvl": "aipar.gvl",
            "file_st": "aipar_update.st",
            "desc_gvl": "Используется для хранения, инициализации и передачи на ВУ значений и состояния входных аналоговых параметров",
            "desc_st": "Используется для обработки входных аналоговых параметров",
            "global_var": "aipar",
            "needs_cycle": True
        },
        "Taopar": {
            "sheet_name": "Вых.А сигн.",
            "file_gvl": "aopar.gvl",
            "file_st": "aopar_update.st",
            "desc_gvl": "Используется для хранения, инициализации и передачи на ВУ значений и состояния выходных аналоговых параметров",
            "desc_st": "Используется для обработки выходных аналоговых параметров",
            "global_var": "aopar",
            "needs_cycle": False
        },
        "Tdipar": {
            "sheet_name": "Вх.Д сигн.",
            "file_gvl": "dipar.gvl",
            "file_st": "dipar_update.st",
            "desc_gvl": "Используется для хранения, инициализации и передачи на ВУ значений и состояния входных дискретных параметров",
            "desc_st": "Используется для обработки входных дискретных параметров",
            "global_var": "dipar",
            "needs_cycle": False
        },
        "Tdopar": {
            "sheet_name": "Вых.Д сигн.",
            "file_gvl": "dopar.gvl",
            "file_st": "dopar_update.st",
            "desc_gvl": "Используется для хранения, инициализации и передачи на ВУ значений и состояния выходных дискретных параметров",
            "desc_st": "Используется для обработки выходных дискретных параметров",
            "global_var": "dopar",
            "needs_cycle": False
        },
        "Tfpl": {
            "sheet_name": "Шлейфы", 
            "file_gvl": "fpl.gvl",
            "file_st": "fpl_update.st",
            "desc_gvl": "Используется для хранения, инициализации и передачи на ВУ значений и состояния пожарных шлейфов",
            "desc_st": "Используется для обработки пожарных шлейфов",
            "global_var": "fpl",
            "needs_cycle": False,
            "plc_common_type": "TfpsLoop"
        }
    }

    # --- ПРАВИЛА ВАЛИДАЦИИ ---
    VALIDATION_RULES = {
        "Taipar": {
            "empty_name": "Пустое алгоритмическое имя",
            "spaces_in_name": "Пробелы в алгоритмическом имени",
            "cyrillic_in_name": "Кириллица в алгоритмическом имени",
            "duplicate_address": "Повторяющиеся физические адреса",
            "missing_limits": "Отсутствие пределов измерения (MIN/MAX)",
            "limits_order": "Ошибка пределов (MIN >= MAX)"
        },
        "Taopar": {
            "empty_name": "Пустое алгоритмическое имя",
            "spaces_in_name": "Пробелы в алгоритмическом имени",
            "cyrillic_in_name": "Кириллица в алгоритмическом имени",
            "duplicate_address": "Повторяющиеся физические адреса"
        },
        "Tdipar": {
            "empty_name": "Пустое алгоритмическое имя",
            "spaces_in_name": "Пробелы в алгоритмическом имени",
            "cyrillic_in_name": "Кириллица в алгоритмическом имени",
            "duplicate_address": "Повторяющиеся физические адреса"
        },
        "Tdopar": {
            "empty_name": "Пустое алгоритмическое имя",
            "spaces_in_name": "Пробелы в алгоритмическом имени",
            "cyrillic_in_name": "Кириллица в алгоритмическом имени",
            "duplicate_address": "Повторяющиеся физические адреса"
        },
        "Tfpl": {
            "empty_name": "Пустое алгоритмическое имя",
            "spaces_in_name": "Пробелы в алгоритмическом имени",
            "cyrillic_in_name": "Кириллица в алгоритмическом имени",
            "duplicate_address": "Повторяющиеся физические адреса"
        }
    }

    # --- ИМЕНА ЛИСТОВ ---
    SHEET_SETTINGS = "Настройки"
    SHEET_AI = "Вх.А сигн."
    SHEET_AO = "Вых.А сигн."
    SHEET_DI = "Вх.Д сигн."
    SHEET_DO = "Вых.Д сигн."
    SHEET_FPL = "Шлейфы"

    # --- ИМЕНА СТОЛБЦОВ ---
    COL_NUM = "№ п/п"
    COL_DESC = "Наименование сигнала"
    COL_TECH_NAME = "Технол. обозначение"
    COL_ALG_NAME = "Алг. имя"
    COL_SHORT_NAME = "Краткое имя"
    COL_CREATE_CODE = "Создавать код"
    COL_TAG_PREFIX = "Префикс тега"
    COL_MIN_VAL = "Нижний предел измер."
    COL_MAX_VAL = "Верхний предел измер."
    COL_UNITS = "Ед. изм."
    COL_PRECISION = "Точность"
    COL_ELEC_UNITS = "Эл.ед."
    COL_DEVICE = "Поз. обозн. устройства с ПЛК"
    COL_CRATE = "Блок ПЛК (Крейт)"
    COL_MODULE = "Модуль ПЛК"
    COL_CHANNEL = "Канал модуля"
    COL_MODULE_TYPE = "Тип модуля"
    COL_SIGNAL_TYPE = "Тип сигнала"
    COL_SIGNAL_CHAR = "Характеристика сигнала"
    COL_IS_SAFE = "Искробезопасность"
    COL_SUBSYSTEM = "Подсистема"
    COL_GROUPS = ["Группа", "Группы"]
    COL_ADDRESS = "Адрес"                 
    COL_SERVER_CYCLE = "Цикл опроса сервером"
    COL_PLC_CYCLE = "Цикл PLC"
    COL_TYPE = "Тип"
    COL_LL = "Порог АН"
    COL_L1 = "Порог Н"
    COL_L  = "Порог ПН"
    COL_H  = "Порог ПВ"
    COL_H1 = "Порог В"
    COL_HH = "Порог АВ"
    COL_HYSTERESIS = "Гистерезис"
    COL_MAX_RATE = "Макс. скор. изм."  
    COL_FREQ_COEF = "К для частот"     
    COL_DEVICE_CLAMP = "Адрес подключения" 
    COL_CUSTOM_CALL = "Нестанд. вызов"
    COL_CIRCUIT_CONTROL = "Контроль цепи"
    COL_CIRCUIT_PURPOSE = "Назначение цепи"
    COL_F_TYPE = "Тип шлейфа"
    COL_VOTING = "Голосование"
    COL_SP_BASE = "Токовые уставки"



    HEADER_ROW = 2       
    DATA_START_ROW = 4   