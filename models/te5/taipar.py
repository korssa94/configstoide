# models.py
import json
import re

class Taipar:
    def __init__(self, row_number, **kwargs):
        self.row_number = row_number
        
        def _safe_str(val):
            return "" if val is None else str(val).strip()

        self.alg_name = _safe_str(kwargs.get('alg_name')).replace('\n', '')
        self.description = _safe_str(kwargs.get('desc')).replace('\n', ' ')
        self.short_name = _safe_str(kwargs.get('short_name')).replace('\n', ' ')
        self.tech_name = _safe_str(kwargs.get('tech_name')).replace('\n', '')
        self.tag_prefix = _safe_str(kwargs.get('tag_prefix')).replace('\n', '')
        
        self.units = _safe_str(kwargs.get('units')).replace('\n', '')
        self.electrical_units = _safe_str(kwargs.get('electrical_units')).replace('\n', '')
        self.precision = _safe_str(kwargs.get('digit')).replace('\n', '')
        
        self.device = _safe_str(kwargs.get('device'))
        self.crate = _safe_str(kwargs.get('crate')).replace('+', '')
        self.module = _safe_str(kwargs.get('module'))
        self.channel = _safe_str(kwargs.get('channel'))
        self.module_type = _safe_str(kwargs.get('module_type'))
        self.signal_type = _safe_str(kwargs.get('signal_type'))
        self.signal_char = _safe_str(kwargs.get('signal_char'))
        self.device_clamp = _safe_str(kwargs.get('device_clamp'))
        self.clamp = _safe_str(kwargs.get('clamp'))
        
        self.paz = False
        if self.module_type and " " in self.module_type:
            if self.module_type.split(" ")[0] == "R500S":
                self.paz = True

        self.subsystem = _safe_str(kwargs.get('subsystem'))
        raw_groups = _safe_str(kwargs.get('group'))
        self.groups = [g.strip() for g in raw_groups.split(',')] if raw_groups else []
        self.server_cycle = _safe_str(kwargs.get('server_cycle'))
        self.par_type = _safe_str(kwargs.get('type'))
        
        self.max_rate = _safe_str(kwargs.get('max_rate'))
        self.freq_coef = _safe_str(kwargs.get('k'))
        
        self.min_val_str = _safe_str(kwargs.get('min_val'))
        self.max_val_str = _safe_str(kwargs.get('max_val'))
        self.min_val = self._to_float(self.min_val_str)
        self.max_val = self._to_float(self.max_val_str)
        
        self.ll_str = _safe_str(kwargs.get('ll'))
        self.l1_str = _safe_str(kwargs.get('l1'))
        self.l_str  = _safe_str(kwargs.get('l'))
        self.h_str  = _safe_str(kwargs.get('h'))
        self.h1_str = _safe_str(kwargs.get('h1'))
        self.hh_str = _safe_str(kwargs.get('hh'))

        self.ll = self._to_float(self.ll_str)
        self.l1 = self._to_float(self.l1_str)
        self.l  = self._to_float(self.l_str)
        self.h  = self._to_float(self.h_str)
        self.h1 = self._to_float(self.h1_str)
        self.hh = self._to_float(self.hh_str)
        
        self.hysteresis = _safe_str(kwargs.get('hysteresis'))

    def _to_float(self, value):
        if not value or value.lower() == "изменяемая":
            return None
        try:
            return float(str(value).replace(',', '.'))
        except ValueError:
            return None

    def get_full_address(self):
        if all([self.device, self.crate, self.module, self.channel]):
            return f"{self.device}-{self.crate}-{self.module}-{self.channel}"
        return None

    def validate(self, active_rules, valid_subsystems=None):
        errors = []
        
        if valid_subsystems:
            if not self.subsystem:
                errors.append({"msg": "КРИТИЧЕСКАЯ: Не указана Подсистема", "field": "subsystem"})
            else:
                curr_sub = self.subsystem.strip().lower()
                found = False
                for v_sub in valid_subsystems:
                    parts = [p.strip().lower() for p in v_sub.split(" - ")]
                    if curr_sub in parts:
                        found = True
                        break
                if not found:
                    errors.append({"msg": f"КРИТИЧЕСКАЯ: Неизвестная подсистема '{self.subsystem}'", "field": "subsystem"})

        if active_rules.get("empty_name", True):
            if not self.alg_name: 
                errors.append({"msg": "Пустое алгоритмическое имя", "field": "alg_name"})
            
        if active_rules.get("spaces_in_name", True):
            if self.alg_name and " " in str(self.alg_name): 
                errors.append({"msg": "Имя содержит пробелы", "field": "alg_name"})

        if active_rules.get("cyrillic_in_name", True):
            if self.alg_name and re.search('[а-яА-ЯёЁ]', str(self.alg_name)):
                errors.append({"msg": "Имя содержит кириллицу", "field": "alg_name"})

        if active_rules.get("missing_limits", True):
            if self.min_val is None: errors.append({"msg": "Не задан нижний предел", "field": "min_val"})
            if self.max_val is None: errors.append({"msg": "Не задан верхний предел", "field": "max_val"})

        if active_rules.get("limits_order", True):
            # Проверка строгого порядка уставок и пределов
            limits_seq = []
            if self.min_val is not None: limits_seq.append(("MIN", self.min_val))
            if self.ll is not None: limits_seq.append(("LL", self.ll))
            if self.l1 is not None: limits_seq.append(("L1", self.l1))
            if self.l is not None: limits_seq.append(("L", self.l))
            if self.h is not None: limits_seq.append(("H", self.h))
            if self.h1 is not None: limits_seq.append(("H1", self.h1))
            if self.hh is not None: limits_seq.append(("HH", self.hh))
            if self.max_val is not None: limits_seq.append(("MAX", self.max_val))

            for idx in range(len(limits_seq) - 1):
                name1, val1 = limits_seq[idx]
                name2, val2 = limits_seq[idx+1]
                if val1 >= val2:
                    errors.append({"msg": f"Ошибка конфигурирования: {name1} ({val1}) >= {name2} ({val2})", "field": "limits"})
                
        return errors

    def _generate_marker(self, unsubs, unnotifs):
        marker_dict = {}
        cycle = self.server_cycle if self.server_cycle in ["fast", "base", "slow"] else "slow"
        comm = {"cycle": cycle}
        if unsubs: comm["unsubscribe"] = unsubs
        if unnotifs: comm["unnotify"] = unnotifs
        marker_dict["communication"] = comm

        name_dict = {}
        if self.description: name_dict["full"] = self.description
        if self.short_name: name_dict["short"] = self.short_name
        if name_dict: marker_dict["name"] = name_dict

        unit_dict = {}
        if self.units: unit_dict["engineering"] = self.units
        if self.electrical_units: unit_dict["electrical"] = self.electrical_units
        if unit_dict: marker_dict["unit"] = unit_dict

        if self.tech_name:
            if self.tag_prefix:
                marker_dict["tag"] = {"full": f"(@{self.tag_prefix}){self.tech_name}", "short": self.tech_name}
            else:
                marker_dict["tag"] = self.tech_name

        if self.precision: marker_dict["digit"] = self.precision

        conn_dict = {}
        addr = self.get_full_address()
        if addr: conn_dict["module"] = addr
        if self.signal_type: conn_dict["type"] = self.signal_type
        if self.device_clamp: conn_dict["device_clamp"] = self.device_clamp
        if self.clamp: conn_dict["clamp"] = self.clamp
        if conn_dict: marker_dict["connection"] = conn_dict

        if self.subsystem: marker_dict["subsystem"] = self.subsystem
        if self.groups: marker_dict["group"] = self.groups

        json_str = json.dumps(marker_dict, ensure_ascii=False, separators=(',', ':'))
        json_str = json_str.replace("{", "(").replace("}", ")")
        return f"{{attribute 'export' := '{json_str}'}}"

    def get_gvl_string(self):
        unsubs = []
        unnotifs = []
        activation_flags = 0
        
        if self.ll_str: activation_flags += 1
        if self.l1_str: activation_flags += 2
        if self.l_str:  activation_flags += 4
        if self.h_str:  activation_flags += 8
        if self.h1_str: activation_flags += 16
        if self.hh_str: activation_flags += 32

        sp_init = f"setpoint := (activation_flags := {activation_flags}"
        sp_comment = "/Уставки/"

        def process_sp(val_str, name):
            nonlocal sp_init, sp_comment, unsubs, unnotifs
            if val_str and val_str.lower() != "изменяемая":
                v = val_str.replace(',', '.')
                sp_init += f", {name} := {v}, {name}_default := {v}"
                sp_comment += f"/{name} := {v}"
            elif val_str.lower() == "изменяемая":
                unnotifs.append(f"setpoint.{name}")
                sp_comment += f"/{name} изменяемая"
            elif not val_str:
                unsubs.append(f"setpoint.{name}")

        process_sp(self.ll_str, "LLV")
        process_sp(self.l1_str, "L1V")
        process_sp(self.l_str, "LV")
        process_sp(self.h_str, "HV")
        process_sp(self.h1_str, "H1V")
        process_sp(self.hh_str, "HHV")

        if self.hysteresis:
            sp_init += f", hyst := {self.hysteresis.replace(',', '.')}"
        sp_init += ")"

        marker = self._generate_marker(unsubs, unnotifs)
        cfg_init = ""
        
        min_v = self.min_val_str.replace(',', '.') if self.min_val_str else "0.0"
        max_v = self.max_val_str.replace(',', '.') if self.max_val_str else "0.0"
        
        ucv_str = ""
        if self.max_rate.lower() == "контроль обрыва" and self.min_val is not None and self.max_val is not None:
            diapazon = self.max_val - self.min_val
            ucv_str = f", ucv_enabled := TRUE, ucvV := {5 * diapazon}"
        elif self.max_rate:
            ucv_str = f", ucv_enabled := TRUE, ucvV := {self.max_rate.replace(',', '.')}"
        
        k_str = f", k := {self.freq_coef.replace(',', '.')}" if self.freq_coef else ""
        p_type = self.par_type if self.par_type else "0"
        
        cfg_init = f"cfg := (par_type := {p_type}, lolim := {min_v}, hilim := {max_v}{ucv_str}{k_str})"

        subsys_comment = self.subsystem if self.subsystem else ""
        class_type = "Taipar_safety" if self.paz else "Taipar"
        
        return (
            f"\t{marker}\n"
            f"\t{self.alg_name} : {class_type} := ({sp_init}, {cfg_init}); "
            f"//{self.description}/{self.tech_name}/{sp_comment}/{subsys_comment}"
        )

    def get_st_string(self):
        mod_name = ""
        if self.device and self.crate and self.module and self.channel:
            # Надежное форматирование канала до двух знаков
            try:
                ch_num = f"{int(self.channel):02d}"
            except ValueError:
                ch_num = str(self.channel)
                
            mod_name = f"MODULE_{self.device}_{self.crate}_{self.module}"
            
        # Убрана лишняя табуляция (\t) в начале строк
        if self.paz and mod_name:
            return f"aipar.{self.alg_name}(mdl_value := {mod_name}.CH{ch_num}.VALUE, mdl_valid := {mod_name}.CH{ch_num}.VALID, mdl_hwError := {mod_name}.HwError, mdl_safe_state := NOT {mod_name}.FAIL_SAFE_STATE); //{self.description}"
        elif (self.signal_char == "Частота" or self.signal_type == "F") and mod_name:
            return f"aipar.{self.alg_name}(mdl_value := {mod_name}.CH{ch_num}.FREQUENCY, mdl_invalid := {mod_name}.CH{ch_num}.INVALID, mdl_hwError := {mod_name}.HwError); //{self.description}"
        elif self.signal_char != "Частота" and self.signal_type != "F" and mod_name:
            return f"aipar.{self.alg_name}(mdl_value := {mod_name}.CH{ch_num}.VALUE, mdl_status := {mod_name}.CH{ch_num}.STATUS, mdl_hwError := {mod_name}.HwError); //{self.description}"
        else:
            return f"aipar.{self.alg_name}(); //{self.description}"