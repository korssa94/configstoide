from application.settings.app_config import AppConfig

class AlarmConfig(AppConfig):
    """Настройки конфигуратора Сигнализаций"""
    KEYWORD_FILE = ["Д51", "В8", "ТБ51"]
    SHEET_ALARMS = "Сигнализации"
    SHEET_SETTINGS = "Настройки"
    SHEET_DOC = "Документ"
    SHEET_INTERNAL = "Внутренние сигнализации"
    DEFAULT_ALGO_FOLDER = "05_Сигнализации"

    # --- ПОДДЕРЖИВАЕМЫЕ ФУНКЦИИ ---
    SUPPORT_TEXT_UPDATE = True
    SUPPORT_DOC_UPDATE = True
    SUPPORT_COLOR_UPDATE = False

    # --- КАРТА ГЕНЕРАЦИИ ---
    # Описываем, как распределять данные по файлам в зависимости от префикса (типа)
    MODEL_SETTINGS = {
        "alr": {
            "file_gvl": "alr.gvl",
            "file_st": "alr_update.st",
            "global_var": "alr",
            "desc_gvl": "Признаки срабатывания предупредительных сигнализаций",
            "desc_st": "Используется для вызова предупредительных, ограничительных и аварийных (без останова) сигнализаций"
        },
        "trs": {
            "file_gvl": "trs.gvl",
            "file_st": "alr_update.st",
            "global_var": "trs",
            "desc_gvl": "Признаки срабатывания аварийных сигнализаций, не приводящих к останову"
        },
        "lmt": {
            "file_gvl": "lmt.gvl",
            "file_st": "alr_update.st",
            "global_var": "lmt",
            "desc_gvl": "Признаки срабатывания ограничительных сигнализаций"
        },
        "crs": {
            "file_gvl": "crs.gvl",
            "file_st": "crs_update.st",
            "global_var": "crs",
            "desc_gvl": "Признаки срабатывания аварийных сигнализаций, приводящих к останову",
            "desc_st": "Используется для вызова аварийных сигнализаций"
        },
        "ppu": {
            "file_gvl": "ppu.gvl",
            "file_st": "ppu_update.st",
            "global_var": "ppu",
            "desc_gvl": "Признаки срабатывания предпусковых условий",
            "desc_st": "Используется для вызова предпусковых условий"
        }
    }

    # --- ИМЕНА СТОЛБЦОВ (из Talarm.cls) ---
    COL_PARAM = "Параметр"
    COL_PARAM_CODE = "Алг.имя сигнала"
    COL_NUM = "№"
    COL_SETPOINT = "Уставка"
    COL_MESSAGE = "Сообщение"
    COL_TECH_NAME = "Техн. об."
    COL_CONDITION = "Условие"
    COL_TYPE = "Тип"
    COL_ACTION = "Действие"
    COL_DELAY = "T, сек."
    COL_ALG_NAME = "Алг. имя"
    COL_CONDITION_CODE = "Условие (код)"
    COL_FAULT_CODE = "Неисправность (код)"
    COL_SET_CODE = "Взвод (код)"
    COL_RESET_CODE = "Сброс (код)"
    COL_CONDITION_TEXT = "Условие (текст)"
    COL_FAULT_TEXT = "Неисправность (текст)"
    COL_SET_TEXT = "Взвод (текст)"
    COL_RESET_TEXT = "Сброс (текст)"


    # Настройки строк
    HEADER_ROW = 1
    DATA_START_ROW = 2


    # --- ТИПЫ СИГНАЛИЗАЦИЙ (значение колонки COL_TYPE) ---
    ALARM_TYPE_WARNING   = "ПС"   # Предупредительная: пишется в alr (+ ppu если действие критическое)
    ALARM_TYPE_PRESTART  = "ППУ"  # Предпусковые условия: пишется в ppu
    ALARM_TYPE_EMERGENCY = "АС"   # Аварийная: пишется в trs или crs в зависимости от действия
    ALARM_TYPE_LIMITING  = "ОС"   # Ограничительная: пишется в lmt

    # Для ПС: эти действия добавляют объект ppu (помимо alr)
    ACTIONS_ADDING_PPU = ["ХР", "ГР", "БЗ"]
    # Для АС: эти действия делают сигнал критическим (crs); остальные — тревожным (trs)
    ACTIONS_MAKING_CRS = ["АОсс", "АОбс", "ВОсс", "ВОбс", "АО", "ВО", "Пожар"]