import streamlit as st
import pandas as pd
from datetime import date, timedelta
import plotly.express as px
from io import BytesIO
import warnings 


warnings.filterwarnings('ignore')

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
        # Эта дата влияет на общий план и старт ряда активностей
        info_date = st.date_input("**Дата начала контроля ИБ**", value=date.today())
    with c3:
        overall_end = st.session_state.get("overall_end_date")

        if overall_end:
            # Есть итоговая дата – окрашенный блок
            st.markdown(
                f"""
                <div style="
                    display:flex;
                    align-items:center;
                    margin-top:28px;
                    justify-content:center;
                    height: 40px;
                    border-radius: 8px;
                    background-color:#fff7e6;
                    border:1px solid #fa8c16;
                    font-size:14px;
                    font-weight:600;
                    color:#d46b08;
                ">
                    Планируемая дата завершения: {overall_end.strftime('%d.%m.%Y')}
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            # Даты нет — серая заглушка
            st.markdown(
                f"""
                <div style="
                    display:flex;
                    align-items:center;
                    margin-top:28px;
                    justify-content:center;
                    height: 40px;
                    border-radius: 8px;
                    background-color:#f5f5f5;
                    border:1px dashed #bfbfbf;
                    font-size:14px;
                    color:#8c8c8c;
                ">
                    Итоговая дата не рассчитана
                </div>
                """,
                unsafe_allow_html=True,
            )


    with st.container():
        c1, c2 = st.columns(2)
        with c1:
            goals = st.text_area("**Цели и задачи контроля ИБ**", height=100)
        with c2:
            objects = st.text_area("**Объекты контроля ИБ**", height=80)
    st.markdown("</div>", unsafe_allow_html=True)

# Визуальный разделитель между блоками
st.markdown("<br>", unsafe_allow_html=True)

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

# Ещё один визуальный разделитель
st.markdown("<br>", unsafe_allow_html=True)

# --- БАЗА ДАННЫХ КОНТРОЛЕЙ ---
CONTROLS_DB = {
    "Визитка": {"cat": "Опросные листы", "dur": 5},
    "Индекс КБ": {"cat": "Опросные листы", "dur": 5},
    "Комплаенс 152-ФЗ": {"cat": "Опросные листы", "dur": 3},
    "Комплаенс 187-ФЗ": {"cat": "Опросные листы", "dur": 3},
    "Комплаенс ГИС": {"cat": "Опросные листы", "dur": 2},
    "КТ, Лицензирование": {"cat": "Опросные листы", "dur": 2},
    "Безопасная разработка ПО": {"cat": "Опросные листы", "dur": 5},
    "Защищенность среды виртуализации": {"cat": "Опросные листы", "dur": 5},
    '"Здоровье AD"': {"cat": "Инструментальные проверки", "dur": 5},
    "Сканирование уязвимостей внутренней сети": {"cat": "Инструментальные проверки", "dur": 20},
    "Внутренний пентест": {"cat": "Инструментальные проверки", "dur": 20},
    "Проверка информации в Блоке ИБ": {"cat": "Информация и отчет", "dur": 5},  # будет пересчитана
    "Подготовка и согласование Отчета": {"cat": "Информация и отчет", "dur": 1},
}

# Порядок контролей для экспорта и графика
CONTROLS_ORDER = list(CONTROLS_DB.keys())


def key_base_from_name(name: str) -> str:
    return name.replace(" ", "_").replace('"', "")


# --- РАБОТА С РАБОЧИМИ ДНЯМИ ---

def end_date_by_workdays(start: date, duration_workdays: int) -> date:
    """
    Возвращает дату окончания при заданном количестве рабочих дней (понедельник–пятница),
    считая start включительно.
    Выходные (сб/вс) пропускаются, но могут попадать в календарный интервал.
    """
    if duration_workdays <= 0:
        return start
    current = start
    remaining = duration_workdays
    while True:
        if current.weekday() < 5:  # 0-4 = пн-пт
            remaining -= 1
            if remaining == 0:
                return current
        current += timedelta(days=1)


def next_workday(d: date) -> date:
    """
    Возвращает следующий рабочий день после даты d.
    """
    current = d + timedelta(days=1)
    while current.weekday() >= 5:
        current += timedelta(days=1)
    return current


# --- ХЕЛПЕР ДЛЯ ЗАГОЛОВКА ТАБЛИЦЫ ---
def render_table_header(with_order: bool = False):
    if with_order:
        h0, h1, h2, h3, h4, h5 = st.columns([0.4, 3, 1, 2, 1.5, 2])
        h0.markdown("**№**")
    else:
        h1, h2, h3, h4, h5 = st.columns([3, 1, 2, 1.5, 2])
    h1.markdown("**Наименование контроля**")
    h2.markdown("**Включено**")
    h3.markdown("**Дата начала (план)**")
    h4.markdown("**Длительность (раб. дн)**")
    h5.markdown("**Дата завершения (план)**")
    st.markdown("<hr style='margin: 5px 0 15px 0;'>", unsafe_allow_html=True)


# --- РЕНДЕР НЕЗАВИСИМОГО КОНТРОЛЯ ---
def render_control_row_independent(name, default_start: date, with_order: bool = False):
    props = CONTROLS_DB[name]
    default_dur = props["dur"]
    kb = key_base_from_name(name)

    # гарантируем наличие длительности
    if f"{kb}_dur" not in st.session_state:
        st.session_state[f"{kb}_dur"] = default_dur

    if with_order:
        c0, c1, c2, c3, c4, c5 = st.columns([0.4, 3, 1, 2, 1.5, 2])
        order_key = f"{kb}_order"
        with c0:
            st.number_input(
                "№",
                min_value=1,
                value=st.session_state.get(order_key, 1),
                key=order_key,
                label_visibility="collapsed",
            )
    else:
        c1, c2, c3, c4, c5 = st.columns([3, 1, 2, 1.5, 2])

    with c1:
        st.write(f"**{name}**")

    with c2:
        is_checked = st.checkbox("ДА", key=f"{kb}_check", label_visibility="collapsed")

    if is_checked:
        with c3:
            start_val = st.session_state.get(f"{kb}_start", default_start)
            start_val = st.date_input(
                "Start",
                value=start_val,
                key=f"{kb}_start",
                label_visibility="collapsed",
            )

        with c4:
            dur_val = st.number_input(
                "Dur",
                min_value=1,
                value=st.session_state.get(f"{kb}_dur", default_dur),
                key=f"{kb}_dur",
                label_visibility="collapsed",
            )

        # рассчитываем дату окончания по рабочим дням
        end_val = end_date_by_workdays(start_val, int(dur_val))
        st.session_state[f"{kb}_end"] = end_val

        with c5:
            st.date_input(
                "End",
                value=end_val,
                key=f"{kb}_end",
                label_visibility="collapsed",
                disabled=True,
            )
    else:
        with c3:
            st.write("-")
        with c4:
            st.write("-")
        with c5:
            st.write("-")

    st.markdown("<hr style='margin: 5px 0; border-top: 1px dashed #eee;'>", unsafe_allow_html=True)


# --- ВЫЧИСЛЕНИЕ БЛОКА "ПРОВЕРКА ИНФОРМАЦИИ В БЛОКЕ ИБ" + "ОТЧЕТ" ---

def compute_info_and_report(dzo_controls_sorted, instrumental_core):
    """
    1. Суммируем длительности (в рабочих днях) всех включённых контролей ДЗО.
    2. Суммируем длительности выбранных инструментальных проверок (ядро).
    3. Длительность проверки в Блоке ИБ = max(∑ ДЗО, ∑ БИБ) + 5 раб. дн.
    4. Старт проверки = дата окончания первого (по порядку) выбранного контроля ДЗО.
       Если ни один контроль ДЗО не выбран — fallback к info_date.
    5. Окончание проверки считаем по рабочим дням.
    6. Отчет стартует в следующий рабочий день после окончания проверки и длится 1 рабочий день.
    Всё сохраняем в session_state.
    """
    # 1. Суммарная длительность блоков ДЗО
    total_dzo_dur = 0
    for name, props in CONTROLS_DB.items():
        if props["cat"] == "Опросные листы":
            kb = key_base_from_name(name)
            if st.session_state.get(f"{kb}_check", False):
                dur = int(st.session_state.get(f"{kb}_dur", props["dur"]))
                total_dzo_dur += dur

    # 2. Суммарная длительность инструмента
    total_instr_dur = 0
    for name in instrumental_core:
        props = CONTROLS_DB[name]
        kb = key_base_from_name(name)
        if st.session_state.get(f"{kb}_check", False):
            dur = int(st.session_state.get(f"{kb}_dur", props["dur"]))
            total_instr_dur += dur

    # 3. Длительность проверки в БИБ
    pib_name = "Проверка информации в Блоке ИБ"
    pib_kb = key_base_from_name(pib_name)

    pib_dur = max(total_dzo_dur, total_instr_dur) + 5

    # 4. Старт проверки — от даты окончания первого по порядку выбранного ДЗО
    first_dzo_end = None
    for name in dzo_controls_sorted:
        kb = key_base_from_name(name)
        if st.session_state.get(f"{kb}_check", False):
            first_dzo_end = st.session_state.get(f"{kb}_end")
            break

    if first_dzo_end is not None:
        pib_start = next_workday(first_dzo_end)
    else:
        # если ДЗО не выбраны — fallback на дату начала контроля ИБ
        pib_start = next_workday(info_date)

    pib_end = end_date_by_workdays(pib_start, pib_dur)

    st.session_state[f"{pib_kb}_check"] = True
    st.session_state[f"{pib_kb}_dur"] = pib_dur
    st.session_state[f"{pib_kb}_start"] = pib_start
    st.session_state[f"{pib_kb}_end"] = pib_end

    # 5–6. Подготовка и согласование отчета
    report_name = "Подготовка и согласование Отчета"
    report_kb = key_base_from_name(report_name)

    report_dur = 1
    report_start = next_workday(pib_end)
    report_end = report_start

    st.session_state[f"{report_kb}_check"] = True
    st.session_state[f"{report_kb}_dur"] = report_dur
    st.session_state[f"{report_kb}_start"] = report_start
    st.session_state[f"{report_kb}_end"] = report_end

    return total_dzo_dur, total_instr_dur, pib_dur


# --- 3. ВЫБОР КОНТРОЛЕЙ / ПЛАНИРОВАНИЕ ЭТАПОВ ---

st.markdown('<div class="header-box">Планирование этапов (Контроли)</div>', unsafe_allow_html=True)

# --- Блок 3.1. Заполнение в ДЗО опросных листов ---
st.markdown('<div class="header-box" style="font-size:16px;">Заполнение в ДЗО опросных листов</div>', unsafe_allow_html=True)
st.markdown('<div class="form-row">', unsafe_allow_html=True)

# список контролей ДЗО
dzo_controls = [name for name, props in CONTROLS_DB.items() if props["cat"] == "Опросные листы"]

# инициализируем порядок по умолчанию (как в словаре)
for idx, name in enumerate(dzo_controls):
    order_key = f"{key_base_from_name(name)}_order"
    if order_key not in st.session_state:
        st.session_state[order_key] = idx + 1

# сортировка по текущему порядку
dzo_controls_sorted = sorted(
    dzo_controls,
    key=lambda n: st.session_state.get(f"{key_base_from_name(n)}_order", 999),
)

render_table_header(with_order=True)

prev_end = None  # окончание предыдущего выбранного контроля

for name in dzo_controls_sorted:
    kb = key_base_from_name(name)

    if prev_end is None:
        # первый контроль ДЗО — от даты начала контроля ИБ
        default_start = info_date
    else:
        # последующие — со следующего рабочего дня после окончания предыдущего
        default_start = next_workday(prev_end)

    # внутри функция:
    #   - возьмёт default_start только если нет st.session_state[f"{kb}_start"]
    #   - посчитает end по рабочим дням и запишет в session_state[f"{kb}_end"]
    render_control_row_independent(name, default_start=default_start, with_order=True)

    # после рендера обновляем prev_end, если контроль включён
    if st.session_state.get(f"{kb}_check", False):
        prev_end = st.session_state.get(f"{kb}_end", prev_end)

st.markdown("</div>", unsafe_allow_html=True)


# --- Блок 3.2. Инструментальные проверки ---
st.markdown('<div class="header-box" style="font-size:16px;">Инструментальные проверки</div>', unsafe_allow_html=True)
st.markdown('<div class="form-row">', unsafe_allow_html=True)
render_table_header(with_order=False)
instrumental_core = ['"Здоровье AD"', "Сканирование уязвимостей внутренней сети", "Внутренний пентест"]
for name in instrumental_core:
    render_control_row_independent(name, default_start=info_date, with_order=False)
st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- Блок 3.3. Проверка информации в Блоке ИБ + Отчет ---
total_dzo_dur, total_instr_dur, pib_dur = compute_info_and_report(dzo_controls_sorted, instrumental_core)

st.markdown('<div class="header-box" style="font-size:16px;">Проверка информации в Блоке ИБ и подготовка отчета</div>', unsafe_allow_html=True)
st.markdown('<div class="form-row">', unsafe_allow_html=True)
render_table_header(with_order=False)

# Рендер статичных строк для проверки и отчета
for name in ["Проверка информации в Блоке ИБ", "Подготовка и согласование Отчета"]:
    kb = key_base_from_name(name)
    dur = st.session_state.get(f"{kb}_dur", CONTROLS_DB[name]["dur"])
    start = st.session_state.get(f"{kb}_start", info_date)
    end = st.session_state.get(f"{kb}_end", end_date_by_workdays(start, int(dur)))

    c1, c2, c3, c4, c5 = st.columns([3, 1, 2, 1.5, 2])

    with c1:
        st.write(f"**{name}**")
        if name == "Проверка информации в Блоке ИБ":
            st.caption(
                "• Старт от даты окончания первого выбранного контроля ДЗО "
                "(если ДЗО не выбраны — от даты начала контроля ИБ)."
            )
            st.caption(
                f"• Длительность = max(∑ ДЗО = {total_dzo_dur}; "
                f"∑ БИБ = {total_instr_dur}) + 5 = {dur} раб. дн."
            )
        if name == "Подготовка и согласование Отчета":
            st.caption("• Старт в следующий рабочий день после окончания проверки в БИБ, длительность 1 раб. дн.")

    with c2:
        st.write("ДА")
        st.session_state[f"{kb}_check"] = True

    with c3:
        st.date_input(
            "Start",
            value=start,
            key=f"{kb}_start",
            label_visibility="collapsed",
            disabled=True,
        )

    with c4:
        st.number_input(
            "Dur",
            min_value=1,
            value=int(dur),
            key=f"{kb}_dur",
            label_visibility="collapsed",
            disabled=True,
        )

    with c5:
        st.date_input(
            "End",
            value=end,
            key=f"{kb}_end",
            label_visibility="collapsed",
            disabled=True,
        )

    st.markdown("<hr style='margin: 5px 0; border-top: 1px dashed #eee;'>", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# --- 4. РАСЧЕТ И РЕЗУЛЬТАТ ---
st.markdown("### Результаты планирования (нажать дважды)")

if st.button("Рассчитать план и График", type="primary"):
    # считаем и сохраняем всё в session_state
    st.session_state["plan_ready"] = True
    
if st.session_state.get("plan_ready"):    
    final_schedule = []

    for name in CONTROLS_ORDER:
        props = CONTROLS_DB[name]
        kb = key_base_from_name(name)

        if not st.session_state.get(f"{kb}_check", False):
            continue

        start_date = st.session_state.get(f"{kb}_start")
        end_date_inclusive = st.session_state.get(f"{kb}_end")
        duration = int(st.session_state.get(f"{kb}_dur", props["dur"]))

        final_schedule.append(
            {
                "Задача": name,
                "Категория": props["cat"],
                "Начало": start_date,
                "Окончание": end_date_inclusive,
                "Длительность (раб. дн)": duration,
            }
        )

    if not final_schedule:
        st.warning("Не выбрано ни одного контроля.")
    else:
        df = pd.DataFrame(final_schedule)

        # Запоминаем максимальную дату окончания для отображения в шапке
        st.session_state["overall_end_date"] = df["Окончание"].max()


        # --- ОТОБРАЖЕНИЕ ТАБЛИЦЫ ---
        df_display = df.copy()
        df_display["Начало"] = df_display["Начало"].apply(lambda x: x.strftime("%d.%m.%Y"))
        df_display["Окончание"] = df_display["Окончание"].apply(lambda x: x.strftime("%d.%m.%Y"))

        st.subheader("Таблица этапов")
        st.dataframe(
            df_display[["Задача", "Начало", "Окончание", "Длительность (раб. дн)"]].sort_values(by="Начало"),
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
                "text_wrap": True
            })
            cell_center = workbook.add_format({"border": 1, "align": "center", "valign": "vcenter"})

            # ======== БЛОК 1 — ОБЩИЕ СВЕДЕНИЯ ========
            worksheet.merge_range("A1:B1", "План проведения контроля ИБ", bold)

            worksheet.write("A2", "Название ДЗО", cell)
            worksheet.write("B2", dzo_name, cell)
            worksheet.write("A3", "Дата начала контроля ИБ", cell)
            worksheet.write("B3", info_date.strftime("%d.%m.%Y"), cell)

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

            # Опросные листы (в Excel — в базовом порядке)
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

            # Инструментальные проверки (ядро)
            row += 1
            worksheet.merge_range(row, 0, row, 3, "Инструментальные проверки", bold)
            row += 1

            for col, h in enumerate(headers):
                worksheet.write(row, col, h, bold)

            row += 1

            for name in instrumental_core:
                props = CONTROLS_DB[name]
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

            # Проверка информации и отчёт
            row += 1
            worksheet.merge_range(row, 0, row, 3, "Проверка информации в Блоке ИБ и подготовка отчета", bold)
            row += 1

            for col, h in enumerate(headers):
                worksheet.write(row, col, h, bold)

            row += 1

            for name in ["Проверка информации в Блоке ИБ", "Подготовка и согласование Отчета"]:
                props = CONTROLS_DB[name]
                kb = key_base_from_name(name)
                enabled = "ДА"  # эти блоки всегда присутствуют
                start = st.session_state.get(f"{kb}_start")
                end = st.session_state.get(f"{kb}_end")

                worksheet.write(row, 0, name, cell)
                worksheet.write(row, 1, enabled, cell_center)
                worksheet.write(row, 2, start.strftime("%d.%m.%Y"), cell_center)
                worksheet.write(row, 3, end.strftime("%d.%m.%Y"), cell_center)
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
    # Plotly ожидает конец интервала как правую границу, поэтому +1 день
    df_gantt["Окончание_Plotly"] = df_gantt["Окончание"] + timedelta(days=1)

    fig = px.timeline(
        df_gantt.sort_values(by="Начало"),
        x_start="Начало",
        x_end="Окончание_Plotly",
        y="Задача",
        color="Категория",
        text="Длительность (раб. дн)",
        color_discrete_map={
            "Опросные листы": "#7700ff",
            "Инструментальные проверки": "#fe4f13",
            "Информация и отчет": "#0f1828",
        },
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
