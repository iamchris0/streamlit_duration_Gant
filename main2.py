import streamlit as st
import pandas as pd
from datetime import date, timedelta
import plotly.express as px
from io import BytesIO

# --- НАСТРОЙКА СТРАНИЦЫ ---
st.set_page_config(page_title="План проведения контроля ИБ", layout="wide")

# --- CSS СТИЛИ ---
st.markdown(
    """
    <style>
        .block-container { padding-top: 2rem; padding-bottom: 5rem; }
        .header-box {
            background-color: #f0f2f6; padding: 10px; border: 1px solid #d6d6d6;
            border-radius: 5px 5px 0 0; font-weight: bold; text-align: center; font-size: 18px; margin-top: 20px;
        }
        .form-row { border: 1px solid #d6d6d6; border-top: none; padding: 10px; background-color: white; }
        .stTextInput, .stDateInput, .stNumberInput, .stTextArea { margin-bottom: 0px; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("План проведения контроля ИБ")


# --- 1. ОБЩИЕ СВЕДЕНИЯ ---
st.markdown('<div class="header-box">Общие сведения</div>', unsafe_allow_html=True)
with st.container():
    st.markdown('<div class="form-row">', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        dzo_name = st.text_input("**Название ДЗО**", placeholder="Введите название...")
    with c2:
        # Эта дата влияет на правило "Проверки информации" и старт цепочки
        begin_date = st.date_input("**Дата начала контроля ИБ**", value=date.today())
    with c3:
        info_date = st.date_input("**Дата последнего предоставления информации от ДЗО**", value=date.today())


    with st.container():
        c1, c2 = st.columns(2)
        with c1:
            goals = st.text_area("**Цели и задачи контроля ИБ**", height=100)
        with c2:
            objects = st.text_area("**Объекты контроля ИБ**", height=80)
    st.markdown("</div>", unsafe_allow_html=True)

# --- 2. СОСТАВ ГРУППЫ ---
st.markdown('<div class="header-box">Состав группы контроля ИБ</div>', unsafe_allow_html=True)
with st.container():
    st.markdown('<div class="form-row">', unsafe_allow_html=True)
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        group_rt = st.text_area("**ФИО, должности (Ростелеком)**", height=120)
    with col_g2:
        group_dzo = st.text_area("**ФИО, должности (ДЗО)**", height=120)
    st.markdown("</div>", unsafe_allow_html=True)

# --- БАЗА ДАННЫХ КОНТРОЛЕЙ ---
CONTROLS_DB = {
    "Визитка": {"cat": "Опросные листы", "dur": 5},
    "Индекс КБ": {"cat": "Опросные листы", "dur": 5},
    "Комплаенс 152-ФЗ": {"cat": "Опросные листы", "dur": 3},
    "Комплаенс 187-ФЗ": {"cat": "Опросные листы", "dur": 3},
    "Комплаенс ГИС": {"cat": "Опросные листы", "dur": 2},
    "КТ, Лицензирование": {"cat": "Опросные листы", "dur": 2},
    "Безопасная разработка ПО": {"cat": "Опросные листы", "dur": 5},
    '"Здоровье AD"': {"cat": "Инструментальные проверки", "dur": 5},
    "Сканирование уязвимостей": {"cat": "Инструментальные проверки", "dur": 20},
    "Внутренний пентест": {"cat": "Инструментальные проверки", "dur": 20},
    "Проверка информации в Блоке ИБ": {"cat": "Инструментальные проверки", "dur": 1},
    "Подготовка и согласование Отчета": {"cat": "Инструментальные проверки", "dur": 1},
}

# Порядок контролей для цепочки
CONTROLS_ORDER = list(CONTROLS_DB.keys())


def key_base_from_name(name: str) -> str:
    return name.replace(" ", "_").replace('"', "")


# --- ПЕРЕСЧЕТ ЦЕПОЧКИ С УЧЕТОМ ДЛИТЕЛЬНОСТЕЙ ---
def recalc_chain():
    """
    Пересчитываем start/end для всех включенных контролей в цепочке.
    - Первый включенный контроль: start берём из session_state или info_date (если ещё нет).
    - Остальные: start = конец предыдущего + 1 день.
    - Для "Проверка информации в Блоке ИБ": доп. ограничение +5 / +8 дней от info_date.
    - end всегда = start + duration - 1.
    Все значения записываются в session_state, чтобы UI и расчёт совпадали.
    """
    current_cursor = info_date
    first_enabled_seen = False

    # Проверка наличия скана и пентеста для условия "Проверка информации"
    scan_key = key_base_from_name("Сканирование уязвимостей")
    pentest_key = key_base_from_name("Внутренний пентест")
    has_scan = st.session_state.get(f"{scan_key}_check", False)
    has_pentest = st.session_state.get(f"{pentest_key}_check", False)

    for name in CONTROLS_ORDER:
        props = CONTROLS_DB[name]
        kb = key_base_from_name(name)

        # инициализируем длительность, если нет
        dur_key = f"{kb}_dur"
        if dur_key not in st.session_state:
            st.session_state[dur_key] = props["dur"]

        enabled = st.session_state.get(f"{kb}_check", False)
        if not enabled:
            continue

        duration = st.session_state.get(dur_key, props["dur"])

        # старт
        if not first_enabled_seen:
            # первый включённый — даём возможность редактировать start вручную
            start = st.session_state.get(f"{kb}_start", current_cursor)
            first_enabled_seen = True
        else:
            # все последующие — строго по цепочке
            start = current_cursor

        # спец-логика для "Проверка информации..."
        if name == "Проверка информации в Блоке ИБ":
            lag_days = 8 if (has_scan and has_pentest) else 5
            min_start_date = info_date + timedelta(days=lag_days)
            start = max(start, min_start_date)

        end = start + timedelta(days=duration - 1)

        st.session_state[f"{kb}_start"] = start
        st.session_state[f"{kb}_end"] = end

        current_cursor = end + timedelta(days=1)


# Пересчитываем цепочку ДО рендера таблицы, чтобы end всегда соответствовал duration
recalc_chain()

# --- 3. ВЫБОР КОНТРОЛЕЙ ---
st.markdown('<div class="header-box">Планирование этапов (Контроли)</div>', unsafe_allow_html=True)
st.markdown('<div class="form-row">', unsafe_allow_html=True)

# Заголовки
h1, h2, h3, h4, h5 = st.columns([3, 1, 2, 1.5, 2])
h1.markdown("**Наименование контроля**")
h2.markdown("**Включено**")
h3.markdown("**Дата начала (план)**")
h4.markdown("**Длит. (дн)**")
h5.markdown("**Дата завершения (план)**")
st.markdown("<hr style='margin: 5px 0 15px 0;'>", unsafe_allow_html=True)


def render_control_row(name):
    props = CONTROLS_DB[name]
    default_dur = props["dur"]
    kb = key_base_from_name(name)

    # гарантируем наличие длительности
    if f"{kb}_dur" not in st.session_state:
        st.session_state[f"{kb}_dur"] = default_dur

    c1, c2, c3, c4, c5 = st.columns([3, 1, 2, 1.5, 2])

    with c1:
        st.write(f"**{name}**")
        if name == "Проверка информации в Блоке ИБ":
            st.caption("Спец. условие: +5/8 дней от инфо-даты")

    with c2:
        is_checked = st.checkbox("ДА", key=f"{kb}_check", label_visibility="collapsed")

    if is_checked:
        # Старт (для всех отображаем, но первый реально влияет на цепочку,
        # остальные будут переписаны recalc_chain на следующем проходе)
        with c3:
            start_val = st.session_state.get(f"{kb}_start", info_date)
            st.date_input(
                "Start",
                value=start_val,
                key=f"{kb}_start",
                label_visibility="collapsed",
            )

        # Длительность
        with c4:
            st.number_input(
                "Dur",
                min_value=1,
                value=st.session_state.get(f"{kb}_dur", default_dur),
                key=f"{kb}_dur",
                label_visibility="collapsed",
            )

        # Дата окончания — в том же стиле, но только для отображения (цепочка управляет автоматом)
        with c5:
            end_val = st.session_state.get(
                f"{kb}_end",
                st.session_state.get(f"{kb}_start", info_date) + timedelta(days=default_dur - 1),
            )

            st.date_input(
                "End",
                value=end_val,
                key=f"{kb}_end",
                label_visibility="collapsed",
                disabled=True,  # пользователь не может вручную ломать цепочку
            )
    else:
        with c3:
            st.write("-")
        with c4:
            st.write("-")
        with c5:
            st.write("-")

    st.markdown("<hr style='margin: 5px 0; border-top: 1px dashed #eee;'>", unsafe_allow_html=True)


# Рендеринг строк
st.markdown("##### Заполнение в ДЗО опросных листов")
for name, props in CONTROLS_DB.items():
    if props["cat"] == "Опросные листы":
        render_control_row(name)

st.markdown("##### Инструментальные проверки")
for name, props in CONTROLS_DB.items():
    if props["cat"] == "Инструментальные проверки":
        render_control_row(name)

st.markdown("</div>", unsafe_allow_html=True)

# --- 4. РАСЧЕТ И РЕЗУЛЬТАТ ---
st.markdown("### Результаты планирования")

if st.button("Рассчитать план и График", type="primary"):
    final_schedule = []

    # Курсор времени: начинаем с info_date
    current_cursor = info_date

    # Проверка наличия скана и пентеста для условия "Проверка информации"
    scan_key = key_base_from_name("Сканирование уязвимостей")
    pentest_key = key_base_from_name("Внутренний пентест")
    has_scan = st.session_state.get(f"{scan_key}_check", False)
    has_pentest = st.session_state.get(f"{pentest_key}_check", False)

    first_enabled_seen = False

    for name in CONTROLS_ORDER:
        props = CONTROLS_DB[name]
        kb = key_base_from_name(name)

        if not st.session_state.get(f"{kb}_check", False):
            continue

        duration = st.session_state.get(f"{kb}_dur", props["dur"])

        # старт
        if not first_enabled_seen:
            start_date = st.session_state.get(f"{kb}_start", current_cursor)
            first_enabled_seen = True
        else:
            start_date = current_cursor

        if name == "Проверка информации в Блоке ИБ":
            lag_days = 8 if (has_scan and has_pentest) else 5
            min_start_date = info_date + timedelta(days=lag_days)
            start_date = max(start_date, min_start_date)

        end_date_inclusive = start_date + timedelta(days=duration - 1)

        final_schedule.append(
            {
                "Задача": name,
                "Категория": props["cat"],
                "Начало": start_date,
                "Окончание": end_date_inclusive,
                "Длительность (дн)": duration,
            }
        )

        current_cursor = end_date_inclusive + timedelta(days=1)

    if not final_schedule:
        st.warning("Не выбрано ни одного контроля.")
    else:
        df = pd.DataFrame(final_schedule)

        # --- ОТОБРАЖЕНИЕ ТАБЛИЦЫ ---
        df_display = df.copy()
        df_display["Начало"] = df_display["Начало"].apply(lambda x: x.strftime("%d.%m.%Y"))
        df_display["Окончание"] = df_display["Окончание"].apply(lambda x: x.strftime("%d.%m.%Y"))

        st.subheader("Таблица этапов")
        st.dataframe(
            df_display[["Задача", "Начало", "Окончание", "Длительность (дн)"]],
            use_container_width=True,
            hide_index=True,
        )

        # --- EXCEL EXPORT ---
        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            workbook = writer.book
            worksheet = workbook.add_worksheet("Plan")
            writer.sheets["Plan"] = worksheet

            # Форматы
            bold = workbook.add_format({"bold": True, "border": 1, "align": "center", "valign": "vcenter"})
            cell = workbook.add_format({"border": 1, "align": "left", "valign": "top"})
            cell_wrap = workbook.add_format({
                "border": 1,
                "align": "left",
                "valign": "top",
                "text_wrap": True      # включён перенос строк
            })
            cell_center = workbook.add_format({"border": 1, "align": "center", "valign": "vcenter"})

            # ======== БЛОК 1 — ОБЩИЕ СВЕДЕНИЯ ========
            worksheet.merge_range("A1:B1", "План проведения контроля ИБ", bold)

            worksheet.write("A2", "Название ДЗО", cell)
            worksheet.write("B2", dzo_name, cell)
            worksheet.write("A3", "Дата начала контроля ИБ", cell)
            worksheet.write("B3", begin_date.strftime("%d.%m.%Y"), cell)
            worksheet.write("A4", "Дата последнего предоставления информации", cell)
            worksheet.write("B4", info_date.strftime("%d.%m.%Y"), cell)

            worksheet.write("A5", "Цели и задачи контроля ИБ", cell)
            worksheet.write("B5", goals, cell_wrap)
            worksheet.write("A6", "Объекты контроля ИБ", cell)
            worksheet.write("B6", objects, cell_wrap)

            # ======== БЛОК 2 — СОСТАВ ГРУППЫ ========
            worksheet.merge_range("A8:B8", "Состав группы контроля ИБ", bold)

            worksheet.write("A9", 'От ПАО "Ростелеком"', cell)
            worksheet.write("B9", group_rt, cell_wrap)
            worksheet.write("A10", "От ДЗО", cell)
            worksheet.write("B10", group_dzo, cell_wrap)

            # ======== БЛОК 3 — ТАБЛИЦА КОНТРОЛЕЙ ========
            start_row = 12
            worksheet.merge_range(start_row, 0, start_row, 3, "Заполнение в ДЗО опросных листов", bold)

            headers = ["Наименование контроля", "Включено", "Дата начала", "Дата завершения"]
            for col, h in enumerate(headers):
                worksheet.write(start_row + 1, col, h, bold)

            row = start_row + 2

            # Опросные листы
            for name, props in CONTROLS_DB.items():
                if props["cat"] == "Опросные листы":
                    kb = key_base_from_name(name)
                    enabled = "ДА" if st.session_state.get(f"{kb}_check", False) else "НЕТ"
                    if enabled == "ДА":
                        start = st.session_state.get(f"{kb}_start")
                        end = st.session_state.get(f"{kb}_end")
                    else:
                        start = end = ""

                    worksheet.write(row, 0, name, cell)
                    worksheet.write(row, 1, enabled, cell_center)
                    worksheet.write(row, 2, start.strftime("%d.%m.%Y") if enabled == "ДА" else "", cell_center)
                    worksheet.write(row, 3, end.strftime("%d.%m.%Y") if enabled == "ДА" else "", cell_center)
                    row += 1

            # Инструментальные проверки
            row += 1
            worksheet.merge_range(row, 0, row, 3, "Инструментальные проверки", bold)
            row += 1

            for col, h in enumerate(headers):
                worksheet.write(row, col, h, bold)

            row += 1

            for name, props in CONTROLS_DB.items():
                if props["cat"] == "Инструментальные проверки":
                    kb = key_base_from_name(name)
                    enabled = "ДА" if st.session_state.get(f"{kb}_check", False) else "НЕТ"
                    if enabled == "ДА":
                        start = st.session_state.get(f"{kb}_start")
                        end = st.session_state.get(f"{kb}_end")
                    else:
                        start = end = ""

                    worksheet.write(row, 0, name, cell)
                    worksheet.write(row, 1, enabled, cell_center)
                    worksheet.write(row, 2, start.strftime("%d.%m.%Y") if enabled == "ДА" else "", cell_center)
                    worksheet.write(row, 3, end.strftime("%d.%m.%Y") if enabled == "ДА" else "", cell_center)
                    row += 1

            worksheet.set_column("A:A", 40)
            worksheet.set_column("B:D", 18)

        excel_data = output.getvalue()

        st.download_button(
            label="📥 Скачать план в Excel",
            data=excel_data,
            file_name=f"plan_{dzo_name if dzo_name else 'DZO'}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


        # --- ДИАГРАММА ГАНТА ---
        st.subheader("Диаграмма Ганта")

        df_gantt = df.copy()
        df_gantt["Окончание_Plotly"] = df_gantt["Окончание"] + timedelta(days=1)

        fig = px.timeline(
            df_gantt,
            x_start="Начало",
            x_end="Окончание_Plotly",
            y="Задача",
            color="Категория",
            text="Длительность (дн)",
        )

        fig.update_yaxes(autorange="reversed")
        fig.update_layout(
            xaxis_title="Дата",
            yaxis_title=None,
            height=600,
            bargap=0.2,
        )
        fig.update_traces(textposition="inside", insidetextanchor="middle")

        st.plotly_chart(fig, use_container_width=True)
