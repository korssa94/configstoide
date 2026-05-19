import os
import json
import win32com.client
import pythoncom
import streamlit as st
from settings.app_config import AppConfig

def load_settings():
    if os.path.exists(AppConfig.SETTINGS_FILE):
        try:
            with open(AppConfig.SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: return {}
    return {}

def save_settings(settings):
    try:
        with open(AppConfig.SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
    except Exception as e:
        st.error(f"Ошибка при сохранении настроек: {e}")

def sync_addon_path():
    """Спрашивает у Excel актуальный путь к надстройке и тихо сохраняет в настройки"""
    try:
        pythoncom.CoInitialize()
        try:
            excel = win32com.client.GetActiveObject("Excel.Application")
        except Exception:
            excel = win32com.client.Dispatch("Excel.Application")
        
        actual_path = None
        
        try:
            for wb in excel.Workbooks:
                if "надстройка" in wb.Name.lower() and wb.Name.lower().endswith(".xlam"):
                    actual_path = wb.FullName
                    break
        except Exception:
            pass
            
        if not actual_path:
            try:
                for addin in excel.AddIns:
                    if "надстройка" in addin.Name.lower():
                        actual_path = addin.FullName
                        break
            except Exception:
                pass
                
        if actual_path:
            settings = load_settings()
            if settings.get("addon_path") != actual_path:
                settings["addon_path"] = actual_path
                save_settings(settings)
                    
    except Exception:
        pass # В боевом режиме тихо игнорируем ошибки
    finally:
        pythoncom.CoUninitialize()

def on_checkbox_change(key):
    """Коллбэк: сохраняет новое состояние чекбокса в файл"""
    settings = load_settings()
    settings[key] = st.session_state[key]
    save_settings(settings)
