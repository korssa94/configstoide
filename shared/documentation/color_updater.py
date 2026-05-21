import os
from shared.documentation.excel_utils import seamless_excel

def update_configurator_colors(filepath, rows_to_color, config_class, logger):
    """
    Универсальная функция покраски ячеек.
    Получает готовую карту строк от парсера и точечно красит резервы в Excel через xlwings.
    """
    if not rows_to_color:
        logger("🎨 Нет данных для изменения цветов ячеек.", "INFO")
        return

    try:
        with seamless_excel(filepath, logger, print_area_mode="fix") as (app, wb, is_background):
            colored_count = 0

            for sheet_name, rows_dict in rows_to_color.items():
                if sheet_name not in [sh.name for sh in wb.sheets]:
                    continue

                ws = wb.sheets[sheet_name]

                # Читаем до 100 колонок
                headers = ws.range((config_class.HEADER_ROW, 1), (config_class.HEADER_ROW, 100)).value
                if not headers:
                    continue

                # Собираем карту заголовков, беря строго ПЕРВОЕ совпадение
                header_map = {}
                for idx, val in enumerate(headers):
                    if val:
                        val_str = str(val).strip()
                        if val_str not in header_map:
                            header_map[val_str] = idx + 1

                col_alg_name = getattr(config_class, 'COL_ALG_NAME', getattr(config_class, 'COL_PARAM_CODE', None))
                if not header_map.get(col_alg_name):
                    continue

                reserve_rows = [r for r, is_res in rows_dict.items() if is_res]
                if reserve_rows:
                    logger(f"📋 Лист '{sheet_name}': найдено {len(reserve_rows)} резервов.", "INFO")
                else:
                    logger(f"📋 Лист '{sheet_name}': резервные строки не обнаружены", "INFO")

                # Покраска всей строки целиком (обход ограничений Страничного режима)
                for excel_row, is_reserve in rows_dict.items():
                    try:
                        if is_reserve:
                            ws.range(f"{excel_row}:{excel_row}").color = (217, 217, 217)
                            colored_count += 1
                        else:
                            ws.range(f"{excel_row}:{excel_row}").color = None
                    except Exception:
                        pass

            logger(f"🎨 Процесс покраски завершен (выделено резервов: {colored_count}).", "INFO")

    except Exception as e:
        logger(f"❌ Ошибка xlwings при покраске: {str(e)}", "ERROR")