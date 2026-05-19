# models/taopar.py
import json
import re

class Taopar:
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
        
        self.circuit_control = _safe_str(kwargs.get('circuit_control'))
        
        self.min_val_str = _safe_str(kwargs.get('min_val'))
        self.max_val_str = _safe_str(kwargs.get('max_val'))

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

        if active_rules.get("empty_name", True) and not self.alg_name: 
            errors.append({"msg": "Пустое алгоритмическое имя", "field": "alg_name"})
        if active_rules.get("spaces_in_name", True) and self.alg_name and " " in str(self.alg_name): 
            errors.append({"msg": "Имя содержит пробелы", "field": "alg_name"})
        if active_rules.get("cyrillic_in_name", True) and self.alg_name and re.search('[а-яА-ЯёЁ]', str(self.alg_name)):
            errors.append({"msg": "Имя содержит кириллицу", "field": "alg_name"})
        return errors

    def _generate_marker(self):
        marker_dict = {}
        cycle = self.server_cycle if self.server_cycle in ["fast", "base", "slow"] else "slow"
        marker_dict["communication"] = {"cycle": cycle}

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
        kc_str = ""
        if self.circuit_control == "2":
            kc_str = "kc_type := 2, "
            
        min_v = self.min_val_str.replace(',', '.') if self.min_val_str else "0.0"
        max_v = self.max_val_str.replace(',', '.') if self.max_val_str else "0.0"
        p_type = self.par_type if self.par_type else "0"
        
        cfg_init = f"cfg := (par_type := {p_type}, lolim := {min_v}, hilim := {max_v})"
        marker = self._generate_marker()

        class_type = "Taopar_safety" if self.paz else "Taopar"
        subsys_comment = self.subsystem if self.subsystem else ""
        
        return (
            f"\t{marker}\n"
            f"\t{self.alg_name} : {class_type} := ({kc_str}{cfg_init}); "
            f"//{self.description}/{self.tech_name}/{subsys_comment}"
        )

    def get_st_string(self):
        mod_name = ""
        if self.device and self.crate and self.module and self.channel:
            try:
                ch_num = f"{int(self.channel):02d}"
                status_ch = int(self.channel) + 7 
            except ValueError:
                ch_num = str(self.channel)
                status_ch = 7
                
            mod_name = f"MODULE_{self.device}_{self.crate}_{self.module}"
            
        # ИСПРАВЛЕНИЕ: Убрана \t в начале строк
        if self.paz and mod_name:
            return f"aopar.{self.alg_name}(mdl_valid := {mod_name}.CH{ch_num}.VALID, mdl_hwError := {mod_name}.HwError, mdl_safe_state := NOT {mod_name}.FAIL_SAFE_STATE, mdl_value => {mod_name}.CH{ch_num}.VALUE); //{self.description}"
        elif self.circuit_control == "2" and mod_name:
            return f"aopar.{self.alg_name}(kc_ai := aipar.kcao_{self.alg_name}.value, mdl_flt := {mod_name}.STATUS.{status_ch}, mdl_hwError := {mod_name}.HwError, mdl_value => {mod_name}.CH{ch_num}); //{self.description}"
        elif (not self.circuit_control or self.circuit_control == "0") and mod_name:
            return f"aopar.{self.alg_name}(mdl_flt := {mod_name}.STATUS.{status_ch}, mdl_hwError := {mod_name}.HwError, mdl_value => {mod_name}.CH{ch_num}); //{self.description}"
        else:
            return f"aopar.{self.alg_name}(); //{self.description}"