import xml.etree.ElementTree as ET
import os

def build_xml_cache(xml_filepath, target_configs=None, logger=None):
    """Парсит plcopen.xml, извлекая GVL только для указанных конфигураций."""
    cache = {}
    if not os.path.exists(xml_filepath):
        return cache
        
    try:
        tree = ET.parse(xml_filepath)
        root = tree.getroot()

        def strip_ns(tag):
            return tag.split('}')[-1] if '}' in tag else tag

        filter_mode = True if target_configs else False
        configs_to_find = [c.lower() for c in target_configs] if filter_mode else []

        instances = next((el for el in root if strip_ns(el.tag) == 'instances'), None)
        if instances is None: return cache

        configurations_node = next((el for el in instances if strip_ns(el.tag) == 'configurations'), None)
        if configurations_node is None: return cache

        for config in configurations_node:
            if strip_ns(config.tag) != 'configuration': continue
            
            config_name = config.get('name', '').lower()
            if filter_mode and config_name not in configs_to_find:
                continue

            for elem in config.iter():
                if strip_ns(elem.tag) == 'globalVars':
                    orig_gvl = elem.get('name', '')
                    gvl_name = orig_gvl.lower() # Ключ для поиска
                    if not gvl_name: continue
                    
                    if gvl_name not in cache:
                        cache[gvl_name] = {}

                    for var in elem:
                        if strip_ns(var.tag) == 'variable':
                            orig_var = var.get('name', '')
                            var_name = orig_var.lower() # Ключ для поиска
                            v_type, v_comment = "", ""
                            
                            for child in var:
                                tag_name = strip_ns(child.tag)
                                if tag_name == 'type':
                                    for type_child in child:
                                        tc_name = strip_ns(type_child.tag)
                                        v_type = type_child.get('name', tc_name) if tc_name == 'derived' else tc_name
                                        break
                                elif tag_name == 'documentation':
                                    for doc_child in child:
                                        if strip_ns(doc_child.tag) == 'xhtml' and doc_child.text:
                                            # ЖЕСТКОЕ ОТСЕЧЕНИЕ ДО ПЕРВОГО СЛЕША
                                            v_comment = doc_child.text.split('/')[0].strip()
                                            break
                            
                            # Сохраняем и поисковые ключи, и оригинальный регистр
                            cache[gvl_name][var_name] = {
                                'type': v_type, 
                                'comment': v_comment,
                                'orig_gvl': orig_gvl,
                                'orig_var': orig_var
                            }
                            
        if logger and filter_mode:
            total_vars = sum(len(v) for v in cache.values())
            logger(f"XML-кэш изолирован для контроллеров: {', '.join(target_configs)}. Загружено: {total_vars}", "INFO")

    except Exception as e:
        if logger: logger(f"Ошибка при фильтрации XML: {str(e)}", "ERROR")
            
    return cache