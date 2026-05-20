import streamlit as st
from datetime import datetime

def add_log(message, level="INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_entry = {"time": timestamp, "level": level, "message": message}
    
    if 'logs' not in st.session_state:
        st.session_state.logs = []
    st.session_state.logs.append(log_entry)

    # При "живом" добавлении лога мы НЕ рисуем кнопку скачивания (is_finished=False)
    placeholder = st.session_state.get('log_placeholder')
    if placeholder is not None:
        _render_logs_into(placeholder, st.session_state.logs)

def _render_logs_into(placeholder, entries):
    """Рендерит СТРОГО текст логов (без кнопок) в плейсхолдер за один заход."""
    html_lines = []
    for entry in entries:
        color = "red" if entry["level"] == "ERROR" else ("orange" if entry["level"] == "WARNING" else "gray")
        html_lines.append(
            f"<div style='display: flex; align-items: center; font-family: monospace; font-size: 14px; margin-bottom: 2px;'>"
            f"<div style='min-width: 80px;'>{entry['time']}</div>"
            f"<div style='margin: 0 10px; color: #555;'>|</div>"
            f"<div style='min-width: 65px; text-align: center; color: {color}; font-weight: bold;'>{entry['level']}</div>"
            f"<div style='margin: 0 10px; color: #555;'>|</div>"
            f"<div style='flex-grow: 1;'>{entry['message']}</div>"
            f"</div>"
        )
    full_log_html = "".join(html_lines)

    placeholder.empty()
    with placeholder.container():
        with st.expander("🗒 Лог событий", expanded=True):
            st.markdown(full_log_html, unsafe_allow_html=True)

def prepare_log_placeholder():
    """Создаёт два выделенных слота: под бегущий лог и под финальную кнопку."""
    st.session_state.log_placeholder = st.empty()
    st.session_state.btn_placeholder = st.empty()
    
    st.session_state.log_placeholder.empty()
    st.session_state.btn_placeholder.empty()
    
    # ИДЕАЛЬНЫЙ UX: Если логов нет, мы вообще ничего не рисуем. Экран девственно чист.
    # Как только пойдет генерация, первая же строчка, add_log сама развернет экспандер.
    if st.session_state.get('logs'):
        _render_logs_into(st.session_state.log_placeholder, st.session_state.logs)

def finish_logging():
    """Вызывается в самом конце. Отрисовывает яркую кнопку скачивания в свой чистый, не затрёпанный циклом слот."""
    log_placeholder = st.session_state.get('log_placeholder')
    btn_placeholder = st.session_state.get('btn_placeholder')
    entries = st.session_state.get('logs')
    
    if log_placeholder and btn_placeholder and entries:
        # Фиксируем финальное состояние текста лога
        _render_logs_into(log_placeholder, entries)
        
        # Отрисовываем кнопку в абсолютно чистый, не тронутый циклом слот.
        # Это гарантирует, что Streamlit покажет её яркой, активной и без задержек.
        with btn_placeholder.container():
            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            raw_log_text = "\n".join([f"{e['time']} | {e['level'].center(7)} | {e['message']}" for e in entries])
            st.download_button(
                "💾 Скачать лог процесса (.txt)",
                data=raw_log_text,
                file_name=f"plc_log_{datetime.now().strftime('%H-%M-%S')}.txt",
                mime="text/plain",
                key="plc_log_final_clean_download",
                use_container_width=True
            )
            st.markdown("<hr style='margin: 15px 0;'>", unsafe_allow_html=True)

def render_xml_inspector():
    """Отрисовывает блок просмотра и скачивания кэша XML"""
    if 'xml_cache' in st.session_state and st.session_state.xml_cache:
        with st.expander("🔍 Посмотреть / Скачать базу переменных (из XML)", expanded=False):
            from application.scanner import cache_to_df
            df = cache_to_df(st.session_state.xml_cache)
            
            # Показываем таблицу (она компактная и с поиском внутри)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Кнопка скачивания CSV
            csv = df.to_csv(index=False).encode('utf-8-sig')
            
            # Генерируем уникальный ключ, чтобы избежать ошибки DuplicateElementKey
            unique_key = f"xml_download_{datetime.now().strftime('%H%M%S%f')}"
            
            st.download_button(
                "💾 Скачать базу переменных (.csv)",
                data=csv,
                file_name=f"plc_variables_{datetime.now().strftime('%H-%M-%S')}.csv",
                mime="text/csv",
                key=unique_key,
                use_container_width=True
            )