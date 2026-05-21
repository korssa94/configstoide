# models/tfpl.py
import json
import re

class Tfpl:
    def __init__(self, row_number, **kwargs):
        self.row_number = row_number
        
        def _safe_str(val):
            return "" if val is None else str(val).strip()

        self.alg_name = _safe_str(kwargs.get('alg_name')).replace('\n', '')
        self.description = _safe_str(kwargs.get('desc')).replace('\n', ' ')
        self.tech_name = _safe_str(kwargs.get('tech_name')).replace('\n', '')
        
        self.device = _safe_str(kwargs.get('device'))
        self.crate = _safe_str(kwargs.get('crate')).replace('+', '')
        self.module = _safe_str(kwargs.get('module'))
        self.channel = _safe_str(kwargs.get('channel'))
        self.signal_type = _safe_str(kwargs.get('signal_type'))
        self.device_clamp = _safe_str(kwargs.get('device_clamp'))
        self.clamp = _safe_str(kwargs.get('clamp'))
        
        raw_groups = _safe_str(kwargs.get('group'))
        self.groups = [g.strip() for g in raw_groups.split(',')] if raw_groups else []
        self.server_cycle = _safe_str(kwargs.get('server_cycle'))
        self.subsystem = _safe_str(kwargs.get('subsystem'))
        self.circuit_control = _safe_str(kwargs.get('circuit_control'))
        
        # Специфичные поля шлейфов
        self.f_type = _safe_str(kwargs.get('f_type'))
        self.voting = _safe_str(kwargs.get('voting'))
        self.sp0 = _safe_str(kwargs.get('sp0'))
        self.sp1 = _safe_str(kwargs.get('sp1'))
        self.sp2 = _safe_str(kwargs.get('sp2'))
        self.sp3 = _safe_str(kwargs.get('sp3'))
        self.sp4 = _safe_str(kwargs.get('sp4'))

    def get_full_address(self):
        if all([self.device, self.crate, self.module, self.channel]):
            return f"{self.device}-{self.crate}-{self.module}-{self.channel}"
        return None

    def validate(self, active_rules, valid_subsystems=None):
        errors = []
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

        if self.description: 
            marker_dict["name"] = {"full": self.description}

        # --- Маркер alarm (логика для дверей и SQ) ---
        desc_lower = self.description.lower()
        tech_lower = self.tech_name.lower()
        alg_lower = self.alg_name.lower()
        
        is_door = "двери" in desc_lower or "sq" in tech_lower or "sq" in alg_lower
        if is_door and self.voting == "1":
            marker_dict["alarm"] = {"type": "alr"}

        if self.tech_name: 
            marker_dict["tag"] = self.tech_name

        conn_dict = {}
        addr = self.get_full_address()
        if addr: conn_dict["module"] = addr
        if self.signal_type: conn_dict["type"] = self.signal_type
        if self.device_clamp: conn_dict["device_clamp"] = self.device_clamp
        if self.clamp: conn_dict["clamp"] = self.clamp
        if conn_dict: marker_dict["connection"] = conn_dict

        if self.groups: marker_dict["group"] = self.groups

        json_str = json.dumps(marker_dict, ensure_ascii=False, separators=(',', ':'))
        json_str = json_str.replace("{", "(").replace("}", ")")
        return f"{{attribute 'export' := '{json_str}'}}"

    def get_gvl_string(self):
        marker = self._generate_marker()

        def clean_sp(val):
            return val.replace(',', '.') if val else "0"

        sp_str = f"sp0 := {clean_sp(self.sp0)}, sp1 := {clean_sp(self.sp1)}, sp2 := {clean_sp(self.sp2)}, sp3 := {clean_sp(self.sp3)}, sp4 := {clean_sp(self.sp4)}"
        f_type_str = self.f_type if self.f_type else "0"
        voting_str = self.voting if self.voting else "0"

        config_str = f"f_type := {f_type_str}, voting := {voting_str}, {sp_str}"
        subsys_comment = self.subsystem if self.subsystem else ""

        return (
            f"\t{marker}\n"
            f"\t{self.alg_name} : TfpsLoop_A := ({config_str}); "
            f"//{self.description}/{self.tech_name}/{subsys_comment}"
        )

    def get_st_string(self):
        mod_name = ""
        ch_num = ""
        
        if self.device and self.crate and self.module and self.channel:
            try:
                ch_num = f"{int(self.channel):02d}"
            except ValueError:
                ch_num = str(self.channel)
            mod_name = f"MODULE_{self.device}_{self.crate}_{self.module}"

        if mod_name:
            return f"fpl.{self.alg_name}(mdl_value := {mod_name}.CH{ch_num}.VALUE, mdl_flt := {mod_name}.CH{ch_num}.STATUS.5 OR {mod_name}.CH{ch_num}.STATUS.6 OR {mod_name}.CH{ch_num}.STATUS.7 OR {mod_name}.HwError); //{self.description}"
        else:
            return f"fpl.{self.alg_name}(); //{self.description}"