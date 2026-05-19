import re
from shared.settings.translation_rules import TRANSLATION_RULES

def get_rule(code_str):
    """Возвращает перевод по правилу или саму строку, если правила нет"""
    if not code_str:
        return ""
    code_lower = str(code_str).lower()
    return TRANSLATION_RULES.get(code_lower, code_str)

def extract_variables(condition_text):
    """Вытаскивает все переменные формата 'xxx.yyy' из выражения, игнорируя AND/OR/NOT"""
    if not condition_text:
        return []
    
    pattern = r'\b[a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*)+\b'
    matches = re.findall(pattern, condition_text)
    
    # Убираем дубликаты и системные слова, сохраняя порядок
    seen = set()
    result = []
    ignore_words = {"and", "or", "not"}
    
    for match in matches:
        if match.lower() not in ignore_words and match not in seen:
            seen.add(match)
            result.append(match)
            
    return result

def translate_condition(condition_code, xml_cache):
    """
    Главная функция перевода кода в текст.
    xml_cache - это словарь с уже распарсенным plcpen.xml
    """
    if not condition_code:
        return ""
        
    if condition_code.upper() == "TRUE":
        return "Логическая 1"
    if condition_code.upper() == "FALSE":
        return "Логический 0"

    variables = extract_variables(condition_code)
    if not variables:
        return ""

    translated_lines = []
    
    for full_var in variables:
        parts = full_var.split('.')
        gvl_name = parts[0]
        var_name = parts[1] if len(parts) > 1 else ""
        
        # Собираем всё, что после имени переменной (например, setpoint.hh)
        field = ".".join(parts[2:]).lower() if len(parts) > 2 else ""

        # Ищем переменную в нашем быстром кэше XML
        # Структура кэша будет такой: xml_cache[gvl_name_lower][var_name_lower]
        var_data = xml_cache.get(gvl_name.lower(), {}).get(var_name.lower())
        
        translation = ""
        if var_data:
            v_type = var_data.get('type', '')
            v_comment = var_data.get('comment', '')
            orig_var = var_data.get('orig_var', var_name)

            # Правило 1: Тип или GVL
            part1 = ""
            if v_type in ["BOOL", "REAL", "Talarm", ""] or not v_type:
                part1 = get_rule(gvl_name) # Если базовый тип, берем правило от GVL
            else:
                part1 = get_rule(v_type)   # Иначе берем правило от Типа (например, taipar)

            # Правило 2: Наименование (используем оригинальный регистр, если нет комментария)
            part2 = v_comment if v_comment else orig_var

            # Правило 3: Поле (если оно есть и это не value/out)
            part3 = ""
            if field and field not in ["value", "out"]:
                part3 = get_rule(field)

            # Собираем строку
            translation = f"{part1}: {part2}"
            if part3:
                translation += f": {part3}"

            translated_lines.append(f"{full_var} - {translation}")

    # Объединяем все переводы через перенос строки
    return "\n".join(translated_lines)