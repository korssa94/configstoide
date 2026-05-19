import streamlit as st
from datetime import datetime

def add_log(message, level="INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_entry = {"time": timestamp, "level": level, "message": message}
    if 'logs' not in st.session_state: st.session_state.logs = []
    st.session_state.logs.append(log_entry)

def render_logs():
    """Отрисовывает блок логов в интерфейсе Streamlit"""
    if st.session_state.get('logs'):
        with st.expander("🗒 Лог событий", expanded=True):
            for entry in st.session_state.logs:
                color = "red" if entry["level"] == "ERROR" else ("orange" if entry["level"] == "WARNING" else "gray")
                st.markdown(
                    f"<div style='display: flex; align-items: center; font-family: monospace; font-size: 14px; margin-bottom: 2px;'>"
                    f"<div style='min-width: 80px;'>{entry['time']}</div>"
                    f"<div style='margin: 0 10px; color: #555;'>|</div>"
                    f"<div style='min-width: 65px; text-align: center; color: {color}; font-weight: bold;'>{entry['level']}</div>"
                    f"<div style='margin: 0 10px; color: #555;'>|</div>"
                    f"<div style='flex-grow: 1;'>{entry['message']}</div>"
                    f"</div>", 
                    unsafe_allow_html=True
                )
            
            st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
            raw_log_text = "\n".join([f"{e['time']} | {e['level'].center(7)} | {e['message']}" for e in st.session_state.logs])
            st.download_button("💾 Скачать лог (.txt)", data=raw_log_text, file_name=f"plc_log_{datetime.now().strftime('%H-%M-%S')}.txt", mime="text/plain")

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
            st.download_button(
                "💾 Скачать базу переменных (.csv)",
                data=csv,
                file_name=f"plc_variables_{datetime.now().strftime('%H-%M-%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )