# app.py
import sys
import os
import datetime
# --- БЛОК ОЧИСТКИ КЭША ---
# Настраиваем очистку под новые имена доменных пакетов
project_modules = [m for m in sys.modules if any(k in m for k in ["alarm_configurator", "inout_configurator", "shared", "application"])]
for module in project_modules:
    del sys.modules[module]

import streamlit as st
import urllib.parse

# Абсолютные импорты настроек
from application.settings.app_config import AppConfig
from inout_configurator.config import TE5Config
from alarm_configurator.config import AlarmConfig

# Абсолютные импорты парсеров
from inout_configurator.parser import TE5Parser
from alarm_configurator.parser import AlarmParser

# Импорты из новой архитектуры
from application.scanner import find_plcopen_xmls, find_master_and_targets
from application.settings_manager import load_settings, save_settings, sync_addon_path, on_checkbox_change
from application.logger import add_log, prepare_log_placeholder, finish_logging
from application.master_loader import load_master_map
from application.processor import process_configurator

CONFIG_REGISTRY = {
    "TE5": {"config": TE5Config, "parser": TE5Parser},
    "Alarms": {"config": AlarmConfig, "parser": AlarmParser}
}

# Выполняем синхронизацию только 1 раз при старте приложения
if "addon_synced" not in st.session_state:
    sync_addon_path()
    st.session_state.addon_synced = True

st.set_page_config(page_title=f"PLC Generator Pro Max v{AppConfig.APP_VERSION}", layout="wide")
st.title(f"🏭 PLC Code Generator Pro Max GT Edition v{AppConfig.APP_VERSION}")

# --- КАСТОМНЫЙ CSS ДЛЯ STREAMLIT ---
st.markdown("""
<style>
    /* 1. Контейнер: разрешаем перенос пузырьков на новые строки */
    .stMultiSelect div[data-baseweb="select"] > div:first-child {
        flex-wrap: wrap !important;
        padding-bottom: 4px !important;
    }
    
    /* 2. Пузырьки: снимаем жесткое ограничение по ширине, но не даем вылезти за пределы поля */
    .stMultiSelect [data-baseweb="tag"] {
        max-width: 100% !important; 
        margin-bottom: 4px !important;
        margin-top: 4px !important;
    }
    
    /* 3. Текст внутри пузырька: возвращаем СТРОГО в одну строку */
    .stMultiSelect [data-baseweb="tag"] span {
        white-space: nowrap !important; /* Текст в одну строку */
        overflow: hidden !important;
        text-overflow: ellipsis !important; /* Троеточие только если не влезает в экран */
        max-width: none !important;
    }
</style>
""", unsafe_allow_html=True)

user_settings = load_settings()

# Инициализация состояний
if 'logs' not in st.session_state: st.session_state.logs = []
if 'analyzed' not in st.session_state: st.session_state.analyzed = False
if 'process_step' not in st.session_state: st.session_state.process_step = None
if 'ms_counter' not in st.session_state: st.session_state.ms_counter = 0
if 'current_selection' not in st.session_state: st.session_state.current_selection = []
if 'selection_initialized' not in st.session_state: st.session_state.selection_initialized = False
# Сбрасываем live-плейсхолдер на каждом rerun'е (он живёт только в рамках одного запуска скрипта)
st.session_state.log_placeholder = None

target_file_from_excel = st.query_params.get("target_file")
skip_paint_global = bool(target_file_from_excel)

if target_file_from_excel:
    target_file_from_excel = urllib.parse.unquote(target_file_from_excel).strip('"')
    current_file_dir = os.path.normpath(os.path.dirname(target_file_from_excel))
else:
    new_dir = st.text_input("📁 Путь к папке Configs:", value=user_settings.get("base_dir", ""))
    if new_dir != user_settings.get("base_dir", ""):
        user_settings["base_dir"] = new_dir
        save_settings(user_settings)
        st.rerun()
    current_file_dir = new_dir

if current_file_dir and os.path.exists(current_file_dir):
    target_files, master_file, _, final_root = find_master_and_targets(
        current_file_dir, CONFIG_REGISTRY, AppConfig.KEYWORD_MASTER
    )

    if not master_file:
        st.error(f"❌ Мастер-конфигуратор не найден!")
    else:
        default_sel = [f for f in target_files if target_file_from_excel and os.path.normpath(f) == os.path.normpath(target_file_from_excel)]
        
        if not st.session_state.selection_initialized:
            st.session_state.current_selection = default_sel
            st.session_state.selection_initialized = True
            
        def on_ms_change():
            current_counter = st.session_state.get("ms_counter", 0)
            widget_key = f"ms_{current_counter}"
            if widget_key in st.session_state:
                st.session_state.current_selection = st.session_state[widget_key]
            st.session_state.ms_counter = current_counter + 1

        selected_files = st.multiselect(
            "📝 Конфигураторы:", 
            options=target_files, 
            format_func=lambda x: os.path.basename(x), 
            default=st.session_state.current_selection,
            key=f"ms_{st.session_state.ms_counter}",
            on_change=on_ms_change
        )
        
        # --- БЛОК ОПЦИЙ И ВЫБОРА XML ---
        st.subheader("🛠 Настройки процесса")
        col_opt1, col_opt2 = st.columns(2)

        with col_opt1:
            do_sources = st.checkbox("Создать исходники", value=True)
            do_coloring = st.checkbox("Обновить цвета ячеек", 
                          value=user_settings.get("do_coloring", False), 
                          key="do_coloring", 
                          on_change=on_checkbox_change, 
                          args=("do_coloring",))

        with col_opt2:
            do_translation = st.checkbox("Обновить текстовое описание", 
                             value=user_settings.get("do_translation", True), 
                             key="do_translation", 
                             on_change=on_checkbox_change, 
                             args=("do_translation",))
            do_document = st.checkbox("Обновить документ", 
                          value=user_settings.get("do_document", True), 
                          key="do_document", 
                          on_change=on_checkbox_change, 
                          args=("do_document",))

        selected_xml_path = None
        if do_translation and final_root:
            found_xmls, debug_info = find_plcopen_xmls(final_root)
            if found_xmls:
                xml_options = {f"[{f['module']}] {f['name']} ({f['size']//1024} KB)": f['path'] for f in found_xmls}
                selected_label = st.selectbox(
                    "Выберите файл проекта (PLCopen XML):", 
                    options=list(xml_options.keys()),
                    index=0
                )
                selected_xml_path = xml_options[selected_label]
            else:
                st.warning(f"⚠️ Обновление текстового описания пропущено: plcopen.xml не найден.")
                with st.expander("🛠 Дебаг поиска"):
                    for line in debug_info: st.text(line)

        # --- КНОПКА ЗАПУСКА ---
        if st.button("🔍 Запустить процесс", type="primary") or (target_file_from_excel and not st.session_state.analyzed):
            st.session_state.logs = [] # ЖЕСТКО ОБНУЛЯЕМ СТАРЫЙ ЛОГ В МОМЕНТ КЛИКА
            st.session_state.process_step = "analyze"
            st.session_state.analyzed = True
            
        # --- ЛОГ: фиксированная позиция на странице ---
        prepare_log_placeholder()

        # --- БЛОК ОЖИДАНИЯ РЕШЕНИЯ ---
        # Резервируем выделенный слот под аварийный интерфейс
        confirm_placeholder = st.empty()
        
        if st.session_state.process_step == "awaiting_confirm":
            with confirm_placeholder.container():
                st.error(f"❌ Найдено ошибок: {len(st.session_state.file_errors)}. Генерация приостановлена!")
                col_btn1, col_btn2 = st.columns(2) 
                with col_btn1:
                    if st.button("⚠️ Всё равно создать (без ошибочных)", type="primary", use_container_width=True):
                        st.session_state.process_step = "generate_forced"
                        st.rerun()
                with col_btn2:
                    if st.button("🛑 Отменить генерацию", use_container_width=True):
                        st.session_state.process_step = "done"
                        add_log("🛑 Генерация отменена пользователем.", level="ERROR")
                        st.rerun()
        else:
            # КРИТИЧНО: Принудительно выжигаем старые кнопки из DOM
            confirm_placeholder.empty()

        # --- ОСНОВНАЯ ЛОГИКА ---
        if st.session_state.process_step in ["analyze", "generate_forced"]:
            force = (st.session_state.process_step == "generate_forced")

            if not force:
                st.session_state.failed_rows_cache = {} # Очищаем кэш ошибочных строк перед каждым новым анализом
                # Проверяем, если список пустой (значит кнопка только что нажата), пишем старт
                if not st.session_state.logs:
                    add_log("🚀 Старт процесса генерации")
            else:
                add_log("🚀 Принудительная генерация (ошибочные сигналы исключены)")
                
            st.session_state.file_errors = []
            st.session_state.files_to_write = []
            
            master_map = load_master_map(master_file)

            for fp in selected_files:
                try:
                    result = process_configurator(
                        fp, master_map, CONFIG_REGISTRY,
                        options={
                            'do_translation': do_translation,
                            'do_document': do_document,
                            'do_coloring': do_coloring,
                        },
                        master_file=master_file,
                        final_root=final_root,
                        selected_xml_path=selected_xml_path,
                        validations=user_settings.get("validations", {}),
                        logger=add_log,
                        force=force,
                    )
                    if result is None:
                        continue

                    parser, xml_cache, is_ok = result

                    if xml_cache:
                        st.session_state.xml_cache = xml_cache

                    st.session_state.file_errors.extend(parser.errors)
                    if (is_ok or force) and do_sources:
                        st.session_state.files_to_write.extend(parser.files_to_write)
                except Exception as e:
                    add_log(
                        f"❌ Не удалось обработать '{os.path.basename(fp)}': {type(e).__name__}: {e}",
                        level="ERROR"
                    )
                    # Один битый файл не должен валить весь прогон — продолжаем со следующим
                    continue

            if st.session_state.file_errors and not force:
                st.session_state.process_step = "awaiting_confirm"
                st.rerun()
            else:
                if st.session_state.files_to_write:
                    written_count = 0
                    failed_count = 0
                    for item in st.session_state.files_to_write:
                        try:
                            os.makedirs(os.path.dirname(item['path']), exist_ok=True)
                            with open(item['path'], "w", encoding=AppConfig.FILE_ENCODING) as f:
                                f.write(item['text'])
                            written_count += 1
                        except Exception as e:
                            failed_count += 1
                            add_log(
                                f"❌ Не удалось записать '{item['path']}': {type(e).__name__}: {e}",
                                level="ERROR"
                            )
                    if failed_count == 0:
                        add_log(f"✨ Процесс завершен! Файлов создано: {written_count}")
                    else:
                        add_log(
                            f"⚠️ Процесс завершен с ошибками. Записано: {written_count}, не удалось: {failed_count}",
                            level="WARNING"
                        )
                st.session_state.process_step = "done"

        finish_logging()

    from application.logger import render_xml_inspector
    render_xml_inspector()