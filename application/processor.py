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
    """Строит XML-кэш, переводит условия в текст и обновляет тексты в конфигураторе.
    Возвращает построенный xml_cache (или None)."""
    logger("📝 Перевод кода в текст с использованием XML-кэша...")
    xml_cache = build_xml_cache(selected_xml_path, target_configs=ctrls, logger=logger)

    parsed_objects = getattr(parser, 'all_parsed_objects', [])
    for obj in parsed_objects:
        if hasattr(obj, 'trigger_cond') and obj.trigger_cond:
            obj.trigger_text = translate_condition(obj.trigger_cond, xml_cache)
        if hasattr(obj, 'fault_cond') and obj.fault_cond:
            obj.fault_text = translate_condition(obj.fault_cond, xml_cache)
        if hasattr(obj, 'set_code') and obj.set_code:
            obj.set_text = translate_condition(obj.set_code, xml_cache)
        if hasattr(obj, 'reset_code') and obj.reset_code:
            obj.reset_text = translate_condition(obj.reset_code, xml_cache)

    logger("✍️ Обновление текстовых описаний в конфигураторе...", "INFO")
    update_configurator_texts(parser.filepath, parsed_objects, config_class, logger)
    return xml_cache


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

    if (is_ok or force) and options.get('do_translation') and selected_xml_path \
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