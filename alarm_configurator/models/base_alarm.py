# models/alarms/base_alarm.py
import json
import re

class BaseAlarm:
    def __init__(self, row_number, get_val, config):
        self.row_number = row_number
        
        # 1. Автоматически переносим всё из kwargs в атрибуты класса
        self.param = str(get_val(config.COL_PARAM)).strip()
        self.param_code = str(get_val(config.COL_PARAM_CODE)).strip()
        self.num = str(get_val(config.COL_NUM)).strip()
        self.setpoint = str(get_val(config.COL_SETPOINT)).strip()

        # Очищаем внутренние переносы строк и лишние пробелы
        raw_message = str(get_val(config.COL_MESSAGE)).strip()
        self.message = re.sub(r'\s+', ' ', raw_message)

        self.tech_name = str(get_val(config.COL_TECH_NAME)).strip()
        
        # Очищаем внутренние переносы строк и лишние пробелы
        raw_condition = str(get_val(config.COL_CONDITION)).strip()
        self.condition = re.sub(r'\s+', ' ', raw_condition)

        self.type = str(get_val(config.COL_TYPE)).strip() 
        self.action = str(get_val(config.COL_ACTION)).strip()
        self.delay = str(get_val(config.COL_DELAY)).strip()
        self.alg_name = str(get_val(config.COL_ALG_NAME)).strip()
        self.condition_code = str(get_val(config.COL_CONDITION_CODE)).strip()
        self.fault_code = str(get_val(config.COL_FAULT_CODE)).strip()
        self.set_code = str(get_val(config.COL_SET_CODE)).strip()
        self.reset_code = str(get_val(config.COL_RESET_CODE)).strip()

        # 2. Теперь вычисляем trigger_cond и fault_cond, используя уже готовые атрибуты self
        self.trigger_cond = "FALSE"
        self.fault_cond = "FALSE"

        if self.condition_code and self.condition_code != "None":
            self.trigger_cond = self.condition_code
            if self.type == "АС":
                self.fault_cond = self.fault_code
        else:
            # Логика сборки условий через aipar/dipar
            if self.setpoint == "" and self.condition == "DI":
                self.trigger_cond = f"dipar.{self.param_code}.value"
                if self.type == "АС":
                    self.fault_cond = f"dipar.{self.param_code}.flt"
            
            elif self.setpoint == "N":
                self.trigger_cond = f"NOT dipar.{self.param_code}.value"
                if self.type == "АС":
                    self.fault_cond = f"dipar.{self.param_code}.flt"
            
            elif self.setpoint in ["LL", "L1", "L", "H", "H1", "HH"]:
                self.trigger_cond = f"aipar.{self.param_code}.setpoint.{self.setpoint}"
                if self.type == "АС":
                    self.fault_cond = f"aipar.{self.param_code}.flt OR NOT aipar.{self.param_code}.setpoint.is{self.setpoint}"
        
        @staticmethod
        def clean_val(val):
            """Очистка текста из ячеек Excel от технических артефактов"""
            if val is None:
                return ""
            # Удаляем артефакт XML, убираем \r и лишние пробелы по краям
            return str(val).replace("_x000D_", "").replace("\r", "").strip()
        
        self.trigger_text = clean_val(get_val(config.COL_CONDITION_TEXT))
        self.fault_text = clean_val(get_val(config.COL_FAULT_TEXT))
        self.set_text = clean_val(get_val(config.COL_SET_TEXT))
        self.reset_text = clean_val(get_val(config.COL_RESET_TEXT))

        #Подсистема
        self.subsystem_name = ""
        self.subsystem_code = ""
        self.subsystem_num = ""
        


    def _generate_base_marker(self):
        """Базовый словарь для JSON-маркера"""
        marker_dict = {}
        if self.message: marker_dict["name"] = self.message
        if self.tech_name: marker_dict["tag"] = self.tech_name
        
        # Блок alarm
        marker_dict["alarm"] = {
            "number": self.num,
            "type": "", # Заполнится в дочернем классе
            "action": self.action if self.action else "нет"
        }
        return marker_dict

    def get_gvl_string(self):
        """Переопределяется в дочерних классах"""
        return ""

    def get_st_string(self):
        """Переопределяется в дочерних классах"""
        return ""
    
    def get_gvl_header(self):
        """Возвращает стандартную декларативную часть GVL"""
        res = "{attribute 'qualified_only'}\n"
        res += "{attribute 'symbol' := 'read'}\n"
        res += "VAR_GLOBAL\n"
        res += "\t{attribute 'symbol' := 'none'}\n"
        res += "\tcommon : Talarm; //Общий сигнал для VAR_STAT\n\n"
        return res

