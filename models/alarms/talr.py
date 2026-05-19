import json
from .base_alarm import BaseAlarm

class Talr(BaseAlarm):
    def __init__(self, row_number, get_val, config, prefix="alr"):
        super().__init__(row_number, get_val, config)
        
        self.prefix = prefix
        self.plc_type = "Talarm"

        # Вычисляем type_num по аналогии с VBA
        self.type_num = ""
        if self.prefix == "alr":
            self.type_num = "1"
        elif self.prefix == "lmt":
            self.type_num = "2"
        elif self.prefix == "trs":
            self.type_num = "3"

    def _generate_marker(self):
        marker_dict = self._generate_base_marker()
        
        # Заполняем тип префикса
        marker_dict["alarm"]["type"] = self.prefix

        # Блок condition (условия, взвод, сброс)
        condition_dict = {
            "active": {"alg": self.trigger_cond},
            "set": "TRUE" if not self.set_code else self.set_code,
            "reset": "FALSE" if not self.reset_code else self.reset_code
        }
        marker_dict["condition"] = condition_dict
        marker_dict["subsystem"] = self.subsystem_name

        json_str = json.dumps(marker_dict, ensure_ascii=False, separators=(',', ':'))
        json_str = json_str.replace("{", "(").replace("}", ")")
        return f"{{attribute 'export' := '{json_str}'}}"

    def get_gvl_string(self):
        marker = self._generate_marker()
        
        # Собираем инициализацию (subsystem_num, type_num, pt)
        params = []
        if self.subsystem_num: 
            params.append(f"subsystem_num := {self.subsystem_num}")
        if self.type_num: params.append(f"type_num := {self.type_num}")
        delay_val = self.delay.replace(',', '.') if self.delay else "0"
        params.append(f"pt := t#{delay_val}s")
        
        init_str = f"({', '.join(params)})" if params else ""
        
        comment = f"//{self.message}/{self.tech_name}/{self.condition}/{self.subsystem_name}"
        return f"\t{marker}\n\t{self.alg_name} : {self.plc_type}:= {init_str}; {comment}"

    def get_st_string(self):
        # Формируем вызов как в эталоне
        res = f"//{self.message}\n"
        res += f"{self.prefix}.{self.alg_name}(\n"
        res += f"in     := {self.trigger_cond},\n"

        cmd_on = self.set_code if self.set_code else "TRUE"
        cmd_off = self.reset_code if self.reset_code else "FALSE"
        res += f"cmd_on := {cmd_on}, cmd_off  := {cmd_off});\n"
        
        res += "//--------------------------------------------------------------------------\n"
        return res
    
    def get_gvl_header(self):
        res = super().get_gvl_header()
        if self.prefix == "trs":
            # Если для ТрС нужны свои переменные (квитирование и т.д.), добавляем их тут
            # res += "\ttrs_ack: BOOL; //Квитирование тревог\n"
            pass
        return res