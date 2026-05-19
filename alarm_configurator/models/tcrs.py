# models/alarms/tcrs.py
import json
from .base_alarm import BaseAlarm

class Tcrs(BaseAlarm):
    def __init__(self, row_number, get_val, config, prefix="crs"):
        super().__init__(row_number, get_val, config)
        
        self.prefix = prefix
        self.plc_type = "Tcrs" # Специфичный тип ФБ для аварийных с остановом
        # Вычисляем type_num по аналогии с VBA
        self.type_num = ""
        if self.action == "АОсс":
            self.type_num = "1"
        elif self.action == "АОбс":
            self.type_num = "2"
        elif self.action == "ВОсс":
            self.type_num = "3"
        elif self.action == "ВОбс":
            self.type_num = "4"
        elif self.action == "АО":
            self.type_num = "5"
        elif self.action == "ВО":
            self.type_num = "6"
        elif self.action == "Пожар":
            self.type_num = "7"
        else:
            self.type_num = ""


    def _generate_marker(self):
        marker_dict = self._generate_base_marker()
        marker_dict["alarm"]["type"] = self.prefix

        # Блок condition (для crs обязательно добавляется fault)
        alg_str = self.trigger_cond if self.trigger_cond else "FALSE"
        fault_str = self.fault_cond if self.fault_cond else "FALSE"
        
        condition_dict = {
            "active": {"alg": alg_str},
            "fault": {"alg": fault_str},
            "set": "TRUE" if not self.set_code else self.set_code,
            "reset": "FALSE" if not self.reset_code else self.reset_code
        }
        marker_dict["condition"] = condition_dict
        marker_dict["subsystem"] = self.subsystem_name

        json_str = json.dumps(marker_dict, ensure_ascii=False, separators=(',', ':'))
        json_str = json_str.replace("{", "(").replace("}", ")")
        return f"{{attribute 'export' := '{json_str}'}}"

    def get_gvl_header(self):
        """Специфичная шапка для аварийных сигналов (readwrite и Tcrs)"""
        res = "{attribute 'qualified_only'}\n"
        res += "{attribute 'symbol' := 'readwrite'}\n"
        res += "VAR_GLOBAL\n"
        res += "\t{attribute 'symbol' := 'none'}\n"
        res += "\tcommon: Tcrs; //Общий сигнал для VAR_STAT\n\n"
        return res

    def get_gvl_string(self):
        marker = self._generate_marker()
        
        params = []
        if self.subsystem_num: 
            params.append(f"subsystem_num := {self.subsystem_num}")
        if self.type_num: 
            params.append(f"type_num := {self.type_num}")
        if self.delay: 
            delay_val = self.delay.replace(',', '.')
            params.append(f"pt := t#{delay_val}s")
        
        init_str = f"({', '.join(params)})" if params else ""
        
        comment = f"//{self.message}/{self.tech_name}/{self.condition}/{self.subsystem_name}"
        return f"\t{marker}\n\t{self.alg_name} : {self.plc_type}:= {init_str}; {comment}"

    def get_st_string(self):
        # Формируем вызов с параметром brk и выравниванием как в эталоне
        res = f"//{self.message}\n"
        res += f"{self.prefix}.{self.alg_name}(\n"
        res += f"in        := {self.trigger_cond if self.trigger_cond else 'FALSE'},\n"
        res += f"brk       := {self.fault_cond if self.fault_cond else 'FALSE'},\n"
        
        cmd_on = self.set_code if self.set_code else "TRUE"
        cmd_off = self.reset_code if self.reset_code else "FALSE"
        
        res += f"cmd_on    := {cmd_on}, cmd_off  := {cmd_off});\n"
        res += "//--------------------------------------------------------------------------\n"
        return res