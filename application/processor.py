import os
import re

from shared.parsers.xml_parser import build_xml_cache
from shared.documentation.condition_translator import translate_condition
from shared.documentation.color_updater import update_configurator_colors
from alarm_configurator.documentation.text_updater import update_configurator_texts
from alarm_configurator.documentation.document_updater import update_configurator_document


def _detect_file_type(file_name, config_registry):
    """Определяет тип конфигуратора по имени файла через KEYWORD_FILE из реестра."""
    for k, v in config_registry.items():
        kw = v["config"].KEYWORD_FILE
        keywords = kw if isinstance(kw, list) else [kw]
        if any(keyword in file_name for keyword in keywords):
            return k
    return None


def _apply_translations(parser, config_class, selected_xml_path, ctrls, logger):
    """Заполняет text-атрибуты на объектах сигнализаций:
    - trigger_text/fault_text/set_text/reset_text — из XML-кэша (если XML доступен)
    - condition_display_text — текст столбца 'Условие', собранный из данных ТЭ5

    В конце один раз вызывает update_configurator_texts (если есть что записывать).
    Возвращает построенный xml_cache (или None, если XML не использовался).
    """
    xml_cache = None

    # --- 1. XML-перевод условий (если XML доступен) ---
    if selected_xml_path:
        logger("📝 Перевод кода в текст с использованием XML-кэша...")
        xml_cache = build_xml_cache(selected_xml_path, target_configs=ctrls, logger=logger)

        for obj in parser.all_parsed_objects:
            if hasattr(obj, 'trigger_cond') and obj.trigger_cond:
                obj.trigger_text = translate_condition(obj.trigger_cond, xml_cache)
            if hasattr(obj, 'fault_cond') and obj.fault_cond:
                obj.fault_text = translate_condition(obj.fault_cond, xml_cache)
            if hasattr(obj, 'set_code') and obj.set_code:
                obj.set_text = translate_condition(obj.set_code, xml_cache)
            if hasattr(obj, 'reset_code') and obj.reset_code:
                obj.reset_text = translate_condition(obj.reset_code, xml_cache)

    # --- 2. Текст столбца "Условие" (из данных ТЭ5, собранных в cross_validation) ---
    inout_signals = getattr(parser, 'inout_signals', None)
    if inout_signals:
        updated_count = _build_condition_display_text(
            parser.all_parsed_objects, inout_signals, config_class, logger
        )
        if updated_count > 0:
            logger(f"✍️ Обновлено условий по данным ТЭ5: {updated_count}", "INFO")

    # --- 3. Запись в Excel (один раз) ---
    if selected_xml_path or inout_signals:
        logger("✍️ Обновление текстовых описаний в конфигураторе...", "INFO")
        update_configurator_texts(parser.filepath, parser.all_parsed_objects, config_class, logger)

    return xml_cache


def _build_condition_display_text(parsed_objects, inout_signals, config_class, logger):
    """Для каждой строки сигнализации с пустым "Условие (код)" формирует текстовое условие
    (например, "DI" / "Нет DI" / "< 20 °С" / "> 80 °С") из данных ТЭ5 и кладёт в
    obj.condition_display_text.

    Возвращает количество обновлённых строк.

    Правила:
      - obj.condition_code не пустой → строка пропущена (ручной код)
      - obj.setpoint == ""           → "DI"
      - obj.setpoint == "N"          → "Нет DI"
      - obj.setpoint в SETPOINT_LOWS → "< {value} {units}"
      - obj.setpoint в SETPOINT_HIGHS → "> {value} {units}"
      - значения уставок ищем в inout_signals по obj.param_code
      - если значения разные между ПЛК → WARNING, строка не обновляется
      - если значение помечено "изменяемая" → WARNING, строка не обновляется
      - если параметр не найден ни в одном ТЭ5 → молча пропускаем
    """
    if not inout_signals:
        return 0

    # Lookup по контроллерам: {ctrl: {alg_name_lower: signal_dict}}
    lookups_by_ctrl = {
        ctrl: {s["alg_name"].lower(): s for s in signals}
        for ctrl, signals in inout_signals.items()
    }
    ctrl_order = list(inout_signals.keys())

    updated_count = 0
    seen_rows = set()  # один и тот же row_number может быть у нескольких объектов (alr+ppu); обновляем строку один раз

    for obj in parsed_objects:
        if obj.row_number in seen_rows:
            continue
        seen_rows.add(obj.row_number)

        # Только автоформируемые строки (без ручного кода)
        if obj.condition_code and obj.condition_code != "None":
            continue

        setpoint = obj.setpoint

        # Дискретные случаи — без обращения к ТЭ5
        if setpoint == "":
            obj.condition_display_text = "DI"
            updated_count += 1
            continue
        if setpoint == "N":
            obj.condition_display_text = "Нет DI"
            updated_count += 1
            continue

        # Аналоговые — нужен поиск в ТЭ5
        if setpoint in config_class.SETPOINT_LOWS:
            sign = "<"
        elif setpoint in config_class.SETPOINT_HIGHS:
            sign = ">"
        else:
            continue  # неизвестное значение Уставки — пропускаем

        sp_key = setpoint.lower()
        param_key = obj.param_code.lower()

        # Собираем (value, units) по всем ПЛК
        collected = []  # [(ctrl, value, units), ...]
        for ctrl in ctrl_order:
            signal = lookups_by_ctrl[ctrl].get(param_key)
            if signal is None:
                continue
            val = signal["setpoint_values"].get(sp_key)
            if val is None:
                continue
            collected.append((ctrl, val, signal["units"]))

        if not collected:
            continue  # параметра/уставки нет ни в одном ТЭ5 (cross-validation это уже подсветила)

        # Проверка на "изменяемая"
        changeable_ctrls = [
            ctrl for ctrl, val, _ in collected
            if isinstance(val, str) and "изменяемая" in val.lower()
        ]
        if changeable_ctrls:
            logger(
                f"⚠️ Строка {obj.row_number}: уставка '{setpoint}' параметра "
                f"'{obj.param_code}' помечена 'изменяемая' в ТЭ5 (ПЛК: {', '.join(changeable_ctrls)}) — "
                f"столбец 'Условие' не обновлён",
                level="WARNING"
            )
            continue

        # Проверка на расхождение значений между ПЛК
        first_val, first_units = collected[0][1], collected[0][2]
        all_same = all(
            str(v).strip() == str(first_val).strip() and (u or "") == (first_units or "")
            for _, v, u in collected
        )
        if not all_same:
            details = ", ".join(
                f"{ctrl}: {v} {u}".strip() for ctrl, v, u in collected
            )
            logger(
                f"⚠️ Строка {obj.row_number}: расхождение уставки '{setpoint}' параметра "
                f"'{obj.param_code}' между ПЛК ({details}) — столбец 'Условие' не обновлён",
                level="WARNING"
            )
            continue

        # Формируем итоговый текст
        value_str = str(first_val).strip()
        units_str = (first_units or "").strip()
        obj.condition_display_text = f"{sign} {value_str} {units_str}".strip()
        updated_count += 1

    return updated_count


def process_configurator(filepath, master_map, config_registry, options, master_file,
                 final_root, selected_xml_path, validations, logger, force=False):
    """Обрабатывает один конфигуратор: определяет тип → запускает парсер →
    при необходимости делает перевод текстов, обновление документа, покраску.

    options — словарь с булевыми флагами: do_translation, do_document, do_coloring.

    Возвращает кортеж (parser, xml_cache, is_ok), либо None если тип файла
    не определён или к нему не привязан ни один ПЛК в Мастер-конфигураторе.
    """
    file_name = os.path.basename(filepath)
    clean_n = re.sub(r'\s+v\d+\.\d+\.\d+.*$', '', os.path.splitext(file_name)[0]).strip()

    file_type = _detect_file_type(file_name, config_registry)
    if not file_type:
        return None

    ctrls = master_map.get(clean_n, [])
    if not force:
        logger(f"📂 Анализ: {clean_n} (ПЛК: {len(ctrls)})")

    if not ctrls:
        return None

    parser_class = config_registry[file_type]["parser"]
    config_class = config_registry[file_type]["config"]

    parser = parser_class(filepath, final_root, ctrls, config_class, logger=logger)
    parser.master_file = master_file

    is_ok = parser.parse(clean_n, validations.get(file_type, {}), force=force)

    xml_cache = None

    if (is_ok or force) and options.get('do_translation') \
            and getattr(config_class, 'SUPPORT_TEXT_UPDATE', False):
        xml_cache = _apply_translations(parser, config_class, selected_xml_path, ctrls, logger)

    if (is_ok or force) and options.get('do_document') \
            and getattr(config_class, 'SUPPORT_DOC_UPDATE', False):
        logger(f"Обновление документа {clean_n}...", "INFO")
        parsed_objects = getattr(parser, 'all_parsed_objects', [])
        update_configurator_document(filepath, parsed_objects, config_class, logger)

    if (is_ok or force) and options.get('do_coloring') \
            and getattr(config_class, 'SUPPORT_COLOR_UPDATE', False):
        logger("🎨 Анализ и обновление цветов ячеек...", "INFO")
        rows_to_color = getattr(parser, 'rows_to_color', {})
        update_configurator_colors(filepath, rows_to_color, config_class, logger)

    return parser, xml_cache, is_ok