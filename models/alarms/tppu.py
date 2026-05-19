# models/alarms/tppu.py
import json
from .base_alarm import BaseAlarm

class Tppu(BaseAlarm):
    def __init__(self, row_number, get_val, config, prefix="ppu"):
        super().__init__(row_number, get_val, config)
        
        self.prefix = prefix
        self.plc_type = "Talarm"

        # Вычисляем type_num по аналогии с VBA
        self.type_num = ""
        if self.action == "ХР":
            self.type_num = "4"
            self.action_alg = "HR"
        elif self.action == "ГР":
            self.type_num = "5"
            self.action_alg = "GR"
        elif self.action == "БЗ":
            self.type_num = "6"
            self.action_alg = "BZ"

    def _generate_marker(self):
        marker_dict = self._generate_base_marker()
        
        # Заполняем тип префикса
        marker_dict["alarm"]["type"] = self.prefix

        # Блок condition (условия, взвод, сброс)
        alg_str = self.trigger_cond if self.trigger_cond else "FALSE"
        
        condition_dict = {
            "active": {"alg": alg_str},
            "set": f"ppu.check_{self.action_alg}.value",
            "reset": f"NOT ppu.check_{self.action_alg}.value"
        }
        marker_dict["condition"] = condition_dict
        marker_dict["subsystem"] = self.subsystem_name

        json_str = json.dumps(marker_dict, ensure_ascii=False, separators=(',', ':'))
        json_str = json_str.replace("{", "(").replace("}", ")")
        return f"{{attribute 'export' := '{json_str}'}}"

    def get_gvl_string(self):
        marker = self._generate_marker()
        
        # Собираем инициализацию (обычно для ППУ нужен только номер подсистемы)
        params = []
        if self.subsystem_num: 
            params.append(f"subsystem_num := {self.subsystem_num}")
        if self.type_num: params.append(f"type_num := {self.type_num}")

        init_str = f"({', '.join(params)})" if params else ""
        
        comment = f"//{self.message}/{self.tech_name}/{self.condition}/{self.subsystem_name}"
        return f"\t{marker}\n\t{self.alg_name} : {self.plc_type}:= {init_str}; {comment}"

    def get_st_string(self):
        # Формируем вызов с параметрами set и reset (выровнено для красоты)
        res = f"//{self.message}\n"
        res += f"{self.prefix}.{self.alg_name}(\n"
        res += f"in     := {self.trigger_cond if self.trigger_cond else 'FALSE'},\n"
        
        set_str = f"ppu.check_{self.action_alg}.value"
        reset_str = f"NOT ppu.check_{self.action_alg}.value"
        
        res += f"cmd_on := {set_str}, cmd_off  := {reset_str});\n"
        res += "//--------------------------------------------------------------------------\n"
        return res
    
    def get_gvl_header(self):
        # Берем стандартную часть из родителя
        res = super().get_gvl_header()
        
        # Добавляем специфику ППУ
        res += "\t{attribute 'export' := '(\"archive\":\"True\",\"name\":\"Контроль ХР\")'}\n"
        res += "\tcheck_HR: Ttch; //Контроль ХР\n"
        res += "\t{attribute 'export' := '(\"archive\":\"True\",\"name\":\"Контроль ГР\")'}\n"
        res += "\tcheck_GR: Ttch; //Контроль ГР\n"
        res += "\t{attribute 'export' := '(\"archive\":\"True\",\"name\":\"Контроль пуска\")'}\n"
        res += "\tcheck_BZ: Ttch; //Контроль пуска\n"
        res += "\t{attribute 'symbol' := 'none'}\n"
        res += "\tHR: BOOL; //Условия ХР собраны\n"
        res += "\t{attribute 'symbol' := 'none'}\n"
        res += "\tGR: BOOL; //Условия ГР собраны\n"
        res += "\t{attribute 'symbol' := 'none'}\n"
        res += "\tBZ: BOOL; //Условия для пуска собраны\n\n"
        return res