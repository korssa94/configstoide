class AppConfig:
    """Глобальные настройки всего генератора"""
    APP_VERSION = "1.0.0"
    SETTINGS_FILE = "user_settings.json"

    SOURCE_FOLDER = "source"
    SOURCE_EXPORT_FOLDER = "source.export"
    KEYWORD_MASTER = "Конфигурация проекта"

    COLOR_RESERVE = "FFD9D9D9"
    
    ADD_ON = "Надстройка для Excel\\Надстройка.xlam"
    
    FILE_ENCODING = "utf-16"  # Гарантирует UTF-16 LE с BOM при генерации исходников

    MASTER_ROW_CTRL  = "контроллер"
    MASTER_ROW_TE5   = "входы/выходы"
    MASTER_ROW_TB51  = "сигнализации"
