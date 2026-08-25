"""
Demo básica de Streamlit con Finanzas Pro
Ejecutar desde la raíz del proyecto: streamlit run examples/streamlit_demo.py
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path para poder importar src
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

import streamlit as st
from models.member import Member
from models.household import Household
from models.budget import Budget
from models.expense_tracker import ExpenseTracker
from workflow.workflow_manager import WorkflowManager
from models.constants import MetodoReparto
from utils.currency import to_euros

# ====== CONFIGURACIÓN DE PÁGINA ======
st.set_page_config(page_title="Kogar", page_icon="🪹", layout="wide")

# ====== ESTADO DE LA APLICACIÓN ======
# Streamlit guarda estado en st.session_state (persiste entre interacciones)
if "workflow" not in st.session_state:
    budget = Budget()
    tracker = ExpenseTracker()

    household = Household(budget, expense_tracker=tracker)
    st.session_state.workflow = WorkflowManager(household)

wf = st.session_state.workflow

# ====== HEADER ======
st.title("🪹 Kogar - Demo")
st.markdown("**Gestor de finanzas para parejas con reparto justo de gastos**")
st.divider()

# ====== SIDEBAR NAVEGACIÓN ======
st.sidebar.header("📋 Navegación")
st.sidebar.markdown(f"**Fase actual:** `{wf.current_phase.value}`")
st.sidebar.divider()

page = st.sidebar.radio(
    "Selecciona sección:",
    [
        "🏠 Inicio",
        "👥 Registro",
        "📊 Planificación",
        "📈 Resumen",
        "🔬 Análisis Avanzado",
    ],
)

# ====== PÁGINA: INICIO ======
if page == "🏠 Inicio":
    st.header("Bienvenido a Finanzas Pro")

    st.info("""
    **¿Qué hace esta app?**
    
    Ayuda a parejas/roommates a dividir gastos de forma justa según ingresos.
    
    **Flujo:**
    1. 👥 **Registro**: Agrega miembros e ingresos
    2. 📊 **Planificación**: Define presupuestos por categoría
    3. 📈 **Resumen**: Ve quién paga cuánto
    4. 🔬 **Análisis**: Simulaciones y recomendaciones
    """)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Miembros registrados", len(wf.get_registered_members()))

    with col2:
        try:
            total_income = wf.get_total_incomes() / 100
            st.metric("Ingresos totales", f"{total_income:.2f}€")
        except ValueError:
            st.metric("Ingresos totales", "0.00€")

    with col3:
        categories = wf.get_active_categories()
        st.metric("Categorías activas", len(categories))

    st.divider()

    # ===== DEMO RÁPIDO =====
    st.subheader("🚀 Prueba Rápida con Datos de Ejemplo")
    st.caption("Carga un escenario predefinido para ver cómo funciona")

    col1, col2 = st.columns(2)

    with col1:
        if st.button(
            "📝 Cargar Ejemplo: Pareja (Amanda & Heri)", use_container_width=True
        ):
            # Reset workflow
            budget = Budget()
            tracker = ExpenseTracker()

            household = Household(budget, expense_tracker=tracker)
            st.session_state.workflow = WorkflowManager(household)
            wf = st.session_state.workflow

            # Registrar miembros
            wf.register_member(Member("Amanda"))
            wf.set_incomes("Amanda", 6000)
            wf.register_member(Member("Heri"))
            wf.set_incomes("Heri", 4000)
            wf.finish_registration()

            # Planificación
            wf.set_standard_categories()
            wf.assign_distribution_method(MetodoReparto.PROPORTIONAL)
            wf.set_budget_for_category("fijos", 5000)
            wf.set_budget_for_category("variables", 2000)
            wf.set_budget_for_category("deuda", 1000)
            wf.set_budget_for_category("ahorro", 500)

            st.success(
                "✅ Ejemplo cargado! Ve a la página **📈 Resumen** para ver los cálculos"
            )
            st.rerun()

    with col2:
        if st.button(
            "👨‍👩‍👧 Cargar Ejemplo: Roommates (3 personas)", use_container_width=True
        ):
            # Reset workflow
            budget = Budget()
            tracker = ExpenseTracker()
            household = Household(budget, expense_tracker=tracker)
            st.session_state.workflow = WorkflowManager(household)
            wf = st.session_state.workflow

            # Registrar miembros
            wf.register_member(Member("Alex"))
            wf.set_incomes("Alex", 5000)
            wf.register_member(Member("Blake"))
            wf.set_incomes("Blake", 3500)
            wf.register_member(Member("Casey"))
            wf.set_incomes("Casey", 2500)
            wf.finish_registration()

            # Planificación
            wf.set_standard_categories()
            wf.assign_distribution_method(MetodoReparto.PROPORTIONAL)
            wf.set_budget_for_category("fijos", 4500)
            wf.set_budget_for_category("variables", 2500)
            wf.set_budget_for_category("deuda", 0)
            wf.set_budget_for_category("ahorro", 1000)

            st.success(
                "✅ Ejemplo cargado! Ve a la página **📈 Resumen** para ver los cálculos"
            )
            st.rerun()

    st.divider()

    # ===== EJEMPLOS DE CÁLCULOS =====
    if wf.current_phase.value == "planificación":
        st.subheader("🧮 Vista Previa de Cálculos")

        try:
            summary = wf.get_planning_summary()

            st.write("**Ejemplo de cómo se calcula el reparto:**")

            # Mostrar fórmula
            total_income = summary["total_household_income"] / 100

            with st.expander("📐 Ver fórmulas matemáticas", expanded=False):
                st.latex(
                    r"\text{Porcentaje de } M = \frac{\text{Ingresos de } M}{\text{Ingresos Totales}} \times 100"
                )
                st.latex(
                    r"\text{Contribución de } M = \text{Presupuesto Categoría} \times \frac{\text{Porcentaje de } M}{100}"
                )

                st.write("**Ejemplo con tus datos:**")
                members = list(summary["member_incomes"].keys())
                if members:
                    member = members[0]
                    income = summary["member_incomes"][member] / 100
                    percentage = (
                        (income / total_income * 100) if total_income > 0 else 0
                    )

                    st.latex(
                        f"\\text{{Porcentaje de {member}}} = \\frac{{{income:.2f}}}{{{total_income:.2f}}} \\times 100 = {percentage:.2f}\\%"
                    )

                    # Ejemplo con una categoría
                    categories_with_budget = [
                        c for c, b in summary["budget_by_category"].items() if b > 0
                    ]
                    if categories_with_budget:
                        cat = categories_with_budget[0]
                        cat_budget = summary["budget_by_category"][cat] / 100
                        contribution = cat_budget * (percentage / 100)

                        st.latex(
                            f"\\text{{Contribución de {member} en {cat}}} = {cat_budget:.2f} \\times \\frac{{{percentage:.2f}}}{{100}} = {contribution:.2f}€"
                        )

            # Mostrar distribución de porcentajes
            st.write("**🎯 Distribución de porcentajes actual:**")

            percentages = summary["distribution_percentages"]

            chart_data = []
            for member, pct_cents in percentages.items():
                pct = pct_cents / 100
                income = summary["member_incomes"][member] / 100
                chart_data.append(
                    {"Miembro": member, "Porcentaje": pct, "Ingresos": income}
                )

            # Mostrar como barras
            for row in chart_data:
                st.write(
                    f"**{row['Miembro']}**: {row['Porcentaje']:.1f}% (Ingresos: {row['Ingresos']:.2f}€)"
                )
                st.progress(row["Porcentaje"] / 100)

        except:
            pass

# ====== PÁGINA: REGISTRO ======
elif page == "👥 Registro":
    st.header("Registrar Miembros del Hogar")

    # Formulario de registro
    with st.form("register_member_form"):
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input("Nombre del miembro", placeholder="Ej: Amanda")

        with col2:
            monthly_income = st.number_input(
                "Ingresos mensuales (€)", min_value=0.0, step=100.0, format="%.2f"
            )

        submitted = st.form_submit_button("➕ Registrar Miembro")

        if submitted:
            try:
                if wf.current_phase.value != "registro":
                    st.error("⚠️ Solo puedes registrar miembros en fase REGISTRO")
                elif not name:
                    st.error("⚠️ El nombre no puede estar vacío")
                else:
                    # Registrar miembro
                    member = Member(name)
                    wf.register_member(member)
                    wf.set_incomes(name, monthly_income)
                    st.success(f"✅ {name} registrado con {monthly_income}€/mes")
                    st.rerun()  # Refrescar para mostrar el nuevo miembro

            except ValueError as e:
                st.error(f"❌ Error: {str(e)}")

    st.divider()

    # Mostrar miembros registrados
    members = wf.get_registered_members()

    if members:
        st.subheader("Miembros actuales")

        for member_name in members:
            income_cents = wf.get_member_income(member_name)
            income_euros = to_euros(income_cents)

            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**{member_name}**")
            with col2:
                st.write(f"`{income_euros}`")

        st.divider()

        # Botón para terminar registro
        if st.button("✅ Finalizar Registro y pasar a Planificación"):
            try:
                wf.finish_registration()
                st.success("✅ Fase REGISTRO completada → Pasando a PLANIFICACIÓN")
                st.rerun()
            except ValueError as e:
                st.error(f"❌ Error: {str(e)}")
    else:
        st.info("👆 Registra al menos un miembro para continuar")

# ====== PÁGINA: PLANIFICACIÓN ======
elif page == "📊 Planificación":
    st.header("Planificar Presupuestos")

    if wf.current_phase.value != "planificación":
        st.warning("⚠️ Debes completar la fase de REGISTRO primero")
    else:
        # Establecer categorías estándar
        if not wf.get_active_categories():
            if st.button(
                "📦 Usar categorías estándar (fijos, variables, deuda, ahorro)"
            ):
                wf.set_standard_categories()
                st.success("✅ Categorías estándar creadas")
                st.rerun()

        categories = wf.get_active_categories()

        if categories:
            st.subheader("Asignar presupuestos")

            # Selector de método de reparto
            method = st.selectbox(
                "Método de distribución:",
                ["PROPORTIONAL", "EQUAL", "CUSTOM"],
                help="PROPORTIONAL: según % de ingresos | EQUAL: 50/50 | CUSTOM: porcentajes manuales",
            )

            wf.assign_distribution_method(MetodoReparto[method])

            # Formulario de presupuestos
            with st.form("budget_form"):
                st.write("Define el presupuesto mensual por categoría:")

                budgets = {}
                for cat in categories:
                    current_budget = wf.household.get_category_budget(cat) / 100
                    budgets[cat] = st.number_input(
                        f"💶 {cat.capitalize()}",
                        min_value=0.0,
                        value=float(current_budget),
                        step=50.0,
                        format="%.2f",
                    )

                if st.form_submit_button("💾 Guardar Presupuestos"):
                    for cat, amount in budgets.items():
                        if amount > 0:
                            wf.set_budget_for_category(cat, amount)
                    st.success("✅ Presupuestos guardados")
                    st.rerun()

            st.divider()

            # Botón para finalizar planificación
            if st.button("✅ Finalizar Planificación"):
                try:
                    wf.finish_planning()
                    st.success("✅ Fase PLANIFICACIÓN completada → Pasando a MES")
                    st.rerun()
                except ValueError as e:
                    st.error(f"❌ Error: {str(e)}")

# ====== PÁGINA: RESUMEN ======
elif page == "📈 Resumen":
    st.header("Resumen Completo y Comparaciones")

    if wf.current_phase.value == "registro":
        st.warning("⚠️ Completa el registro primero")
    elif wf.current_phase.value == "planificación":
        try:
            summary = wf.get_planning_summary()

            # ===== SECCIÓN 1: MÉTRICAS PRINCIPALES =====
            st.subheader("📊 Vista General")

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                total = summary["total_household_income"] / 100
                st.metric("💰 Ingresos Totales", f"{total:.2f}€")

            with col2:
                budgeted = summary["total_budgeted"] / 100
                st.metric("📊 Presupuestado", f"{budgeted:.2f}€")

            with col3:
                loose = summary["loose_money"] / 100
                percentage_budgeted = (budgeted / total * 100) if total > 0 else 0
                st.metric(
                    "💵 Dinero Libre",
                    f"{loose:.2f}€",
                    delta=f"{100 - percentage_budgeted:.1f}% libre",
                )

            with col4:
                num_categories = len(
                    [c for c in summary["budget_by_category"].values() if c > 0]
                )
                st.metric("📁 Categorías Activas", num_categories)

            st.divider()

            # ===== SECCIÓN 2: CONTRIBUCIONES POR MIEMBRO =====
            st.subheader("👥 Contribuciones Totales por Miembro")
            st.caption(f"Método actual: **{summary['distribution_method'].upper()}**")

            # Calcular totales por miembro
            member_totals = {}
            for cat_data in summary["contributions_preview"].values():
                for member, amount in cat_data["contributions"].items():
                    if member not in member_totals:
                        member_totals[member] = 0
                    member_totals[member] += amount

            cols = st.columns(len(member_totals))
            for idx, (member, total_cents) in enumerate(member_totals.items()):
                with cols[idx]:
                    total_euros = total_cents / 100
                    income = summary["member_incomes"][member] / 100
                    percentage = (total_euros / income * 100) if income > 0 else 0

                    st.metric(
                        f"💳 {member}",
                        f"{total_euros:.2f}€",
                        delta=f"{percentage:.1f}% de su sueldo",
                    )

            st.divider()

            # ===== SECCIÓN 3: COMPARACIÓN DE MÉTODOS =====
            st.subheader("⚖️ Comparación de Métodos de Reparto")
            st.caption("Compara cómo cambiarían las contribuciones con cada método")

            # Calcular con los 3 métodos
            methods_comparison = {}
            for method in [MetodoReparto.PROPORTIONAL, MetodoReparto.EQUAL]:
                try:
                    percentages = wf.household.get_percentages_by_method(method)
                    comparison_summary = (
                        wf.household.preview_budget_contribution_summary(method)
                    )

                    # Calcular totales por miembro
                    method_totals = {}
                    for cat_data in comparison_summary.values():
                        for member, amount in cat_data["contributions"].items():
                            if member not in method_totals:
                                method_totals[member] = 0
                            method_totals[member] += amount

                    methods_comparison[method.value] = {
                        "percentages": percentages,
                        "totals": method_totals,
                    }
                except:
                    pass

            # Mostrar comparación
            if methods_comparison:
                comparison_data = []
                members = list(summary["member_incomes"].keys())

                for member in members:
                    row = {"Miembro": member}
                    income = summary["member_incomes"][member] / 100
                    row["Ingresos"] = f"{income:.2f}€"

                    for method_name, data in methods_comparison.items():
                        if member in data["totals"]:
                            total = data["totals"][member] / 100
                            pct = data["percentages"][member] / 100
                            row[f"{method_name.capitalize()}"] = (
                                f"{total:.2f}€ ({pct:.1f}%)"
                            )

                    comparison_data.append(row)

                st.table(comparison_data)

                # Mostrar diferencias
                if len(methods_comparison) == 2:
                    st.caption("💡 **Diferencias entre métodos:**")
                    for member in members:
                        prop_total = (
                            methods_comparison["proporcional"]["totals"].get(member, 0)
                            / 100
                        )
                        equal_total = (
                            methods_comparison["igual"]["totals"].get(member, 0) / 100
                        )
                        diff = prop_total - equal_total

                        if abs(diff) > 0.01:
                            emoji = "📈" if diff > 0 else "📉"
                            st.write(
                                f"{emoji} **{member}**: {abs(diff):.2f}€ {'más' if diff > 0 else 'menos'} con PROPORCIONAL vs IGUAL"
                            )

            st.divider()

            # ===== SECCIÓN 4: DESGLOSE POR CATEGORÍA =====
            st.subheader("📁 Desglose por Categoría")

            contributions = summary["contributions_preview"]

            # Crear tabs por categoría
            category_tabs = st.tabs(
                [
                    cat.capitalize()
                    for cat in contributions.keys()
                    if contributions[cat]["planned"] > 0
                ]
            )

            active_categories = [
                cat for cat in contributions.keys() if contributions[cat]["planned"] > 0
            ]

            for idx, category in enumerate(active_categories):
                with category_tabs[idx]:
                    data = contributions[category]
                    planned_euros = data["planned"] / 100

                    col1, col2 = st.columns([1, 2])

                    with col1:
                        st.metric("💶 Presupuesto", f"{planned_euros:.2f}€")

                        # Calcular porcentaje del total
                        pct_of_total = (
                            (planned_euros / (summary["total_budgeted"] / 100) * 100)
                            if summary["total_budgeted"] > 0
                            else 0
                        )
                        st.caption(f"📊 {pct_of_total:.1f}% del presupuesto total")

                    with col2:
                        st.write("**Contribuciones:**")
                        for member, amount_cents in data["contributions"].items():
                            amount_euros = amount_cents / 100
                            percentage = (
                                (amount_cents / data["planned"] * 100)
                                if data["planned"] > 0
                                else 0
                            )

                            # Progress bar
                            st.write(
                                f"**{member}**: {amount_euros:.2f}€ ({percentage:.1f}%)"
                            )
                            st.progress(percentage / 100)

            st.divider()

            # ===== SECCIÓN 5: ANÁLISIS DE EQUIDAD =====
            st.subheader("⚖️ Análisis de Equidad")
            st.caption("¿Es justo este reparto según los ingresos?")

            for member in summary["member_incomes"].keys():
                income = summary["member_incomes"][member] / 100
                contribution = member_totals.get(member, 0) / 100
                percentage_of_income = (
                    (contribution / income * 100) if income > 0 else 0
                )
                remaining = income - contribution

                col1, col2, col3 = st.columns([2, 1, 1])

                with col1:
                    st.write(f"**{member}**")
                    st.progress(percentage_of_income / 100)

                with col2:
                    st.metric("Aporta", f"{contribution:.2f}€")
                    st.caption(f"{percentage_of_income:.1f}% de su sueldo")

                with col3:
                    st.metric("Le queda", f"{remaining:.2f}€")
                    color = (
                        "🟢"
                        if remaining > income * 0.3
                        else "🟡"
                        if remaining > income * 0.15
                        else "🔴"
                    )
                    st.caption(f"{color} {100 - percentage_of_income:.1f}% libre")

        except ValueError as e:
            st.error(f"Error al obtener resumen: {str(e)}")
    else:
        st.info(f"Fase actual: {wf.current_phase.value.upper()}")

# ====== PÁGINA: ANÁLISIS AVANZADO ======
elif page == "🔬 Análisis Avanzado":
    st.header("Análisis Avanzado y Escenarios")

    if wf.current_phase.value != "planificación":
        st.warning("⚠️ Completa la planificación primero para ver análisis")
    else:
        summary = wf.get_planning_summary()

        # ===== SECCIÓN 1: SIMULADOR DE INGRESOS =====
        st.subheader("💰 Simulador: ¿Qué pasa si cambian los ingresos?")
        st.caption("Simula cómo cambiarían las contribuciones con diferentes salarios")

        members = list(summary["member_incomes"].keys())

        with st.expander("🔧 Ajustar ingresos simulados", expanded=False):
            simulated_incomes = {}
            cols = st.columns(len(members))

            for idx, member in enumerate(members):
                with cols[idx]:
                    original_income = summary["member_incomes"][member] / 100
                    simulated_incomes[member] = st.slider(
                        f"{member}",
                        min_value=0.0,
                        max_value=original_income * 2,
                        value=original_income,
                        step=100.0,
                        format="%.0f€",
                    )

        # Calcular con ingresos simulados
        if any(
            simulated_incomes[m] != summary["member_incomes"][m] / 100 for m in members
        ):
            st.info("🔄 Calculando con nuevos ingresos...")

            # Crear household temporal
            temp_budget = Budget()
            temp_household = Household(temp_budget, wf.household.method)

            for member_name in members:
                temp_household.register_member(Member(member_name))
                temp_household.set_member_income(
                    member_name, simulated_incomes[member_name]
                )

            # Copiar categorías y presupuestos
            for cat in summary["budget_by_category"].keys():
                temp_budget.add_category(cat)
                amount_cents = summary["budget_by_category"][cat]
                if amount_cents > 0:
                    temp_budget.set_budget(cat, amount_cents / 100)

            # Calcular nuevas contribuciones
            temp_percentages = temp_household.get_percentages_by_method(
                wf.household.method
            )
            temp_contributions = temp_household.preview_budget_contribution_summary(
                wf.household.method
            )

            # Calcular totales
            original_totals = {}
            simulated_totals = {}

            for cat_data in summary["contributions_preview"].values():
                for member, amount in cat_data["contributions"].items():
                    if member not in original_totals:
                        original_totals[member] = 0
                    original_totals[member] += amount

            for cat_data in temp_contributions.values():
                for member, amount in cat_data["contributions"].items():
                    if member not in simulated_totals:
                        simulated_totals[member] = 0
                    simulated_totals[member] += amount

            # Mostrar comparación
            st.subheader("📊 Comparación: Original vs Simulado")

            comparison_rows = []
            for member in members:
                original = original_totals.get(member, 0) / 100
                simulated = simulated_totals.get(member, 0) / 100
                diff = simulated - original
                diff_pct = (diff / original * 100) if original > 0 else 0

                comparison_rows.append(
                    {
                        "Miembro": member,
                        "Ingresos Actual": f"{summary['member_incomes'][member] / 100:.0f}€",
                        "Ingresos Simulado": f"{simulated_incomes[member]:.0f}€",
                        "Contribución Actual": f"{original:.2f}€",
                        "Contribución Simulada": f"{simulated:.2f}€",
                        "Diferencia": f"{diff:+.2f}€ ({diff_pct:+.1f}%)",
                    }
                )

            st.table(comparison_rows)

        st.divider()

        # ===== SECCIÓN 2: ANÁLISIS DE SENSIBILIDAD =====
        st.subheader("📈 Análisis de Sensibilidad")
        st.caption("¿Cómo impactan cambios de ±20% en cada presupuesto?")

        categories_with_budget = [
            c for c, b in summary["budget_by_category"].items() if b > 0
        ]

        if categories_with_budget:
            sensitivity_data = []

            for category in categories_with_budget[:3]:  # Limitar a 3 para no saturar
                budget_cents = summary["budget_by_category"][category]
                budget_euros = budget_cents / 100

                # Calcular ±20%
                scenarios = {
                    "-20%": budget_euros * 0.8,
                    "Actual": budget_euros,
                    "+20%": budget_euros * 1.2,
                }

                row = {"Categoría": category.capitalize()}

                for scenario_name, scenario_budget in scenarios.items():
                    # Total household contribution para esta categoría
                    row[scenario_name] = f"{scenario_budget:.2f}€"

                sensitivity_data.append(row)

            st.table(sensitivity_data)

            st.caption(
                "💡 Ajusta presupuestos para mantener el balance deseado entre categorías"
            )

        st.divider()

        # ===== SECCIÓN 3: ESTADÍSTICAS FINANCIERAS =====
        st.subheader("📊 Estadísticas Financieras")

        col1, col2 = st.columns(2)

        with col1:
            st.write("**💳 Carga Financiera por Miembro**")

            member_totals = {}
            for cat_data in summary["contributions_preview"].values():
                for member, amount in cat_data["contributions"].items():
                    if member not in member_totals:
                        member_totals[member] = 0
                    member_totals[member] += amount

            for member in summary["member_incomes"].keys():
                income = summary["member_incomes"][member] / 100
                contribution = member_totals.get(member, 0) / 100
                burden = (contribution / income * 100) if income > 0 else 0

                st.write(f"**{member}**: {burden:.1f}% de ingresos comprometidos")
                st.progress(burden / 100)

                # Interpretación
                if burden < 30:
                    st.caption("🟢 Carga baja - Margen cómodo")
                elif burden < 50:
                    st.caption("🟡 Carga moderada")
                elif burden < 70:
                    st.caption("🟠 Carga alta - Poco margen")
                else:
                    st.caption("🔴 Carga muy alta - Revisar presupuesto")

        with col2:
            st.write("**📁 Distribución de Presupuesto**")

            # Calcular porcentajes por categoría
            total_budgeted = summary["total_budgeted"] / 100

            category_percentages = []
            for cat, amount_cents in summary["budget_by_category"].items():
                if amount_cents > 0:
                    amount = amount_cents / 100
                    pct = (amount / total_budgeted * 100) if total_budgeted > 0 else 0
                    category_percentages.append((cat, pct, amount))

            # Ordenar por porcentaje
            category_percentages.sort(key=lambda x: x[1], reverse=True)

            for cat, pct, amount in category_percentages:
                st.write(f"**{cat.capitalize()}**: {pct:.1f}% ({amount:.2f}€)")
                st.progress(pct / 100)

        st.divider()

        # ===== SECCIÓN 4: RECOMENDACIONES =====
        st.subheader("💡 Recomendaciones del Sistema")

        # Análisis automático
        loose_money = summary["loose_money"] / 100
        total_income = summary["total_household_income"] / 100
        loose_pct = (loose_money / total_income * 100) if total_income > 0 else 0

        if loose_pct > 40:
            st.success(
                f"✅ **Excelente**: Tienes {loose_pct:.0f}% de ingresos sin asignar ({loose_money:.2f}€). Considera aumentar ahorro o crear fondo de emergencia."
            )
        elif loose_pct > 20:
            st.info(
                f"👍 **Bien**: {loose_pct:.0f}% libre ({loose_money:.2f}€). Balance saludable entre presupuesto y flexibilidad."
            )
        elif loose_pct > 5:
            st.warning(
                f"⚠️ **Ajustado**: Solo {loose_pct:.0f}% libre ({loose_money:.2f}€). Poco margen para imprevistos."
            )
        else:
            st.error(
                f"🚨 **Crítico**: Apenas {loose_pct:.0f}% libre ({loose_money:.2f}€). Presupuesto muy ajustado, revisa gastos no esenciales."
            )

        # Comparación con regla 50/30/20
        st.caption("**📋 Comparación con regla 50/30/20:**")
        st.write("Regla financiera popular: 50% necesidades, 30% deseos, 20% ahorro")

        # Intentar clasificar categorías
        essentials = summary["budget_by_category"].get("fijos", 0) / 100
        wants = summary["budget_by_category"].get("variables", 0) / 100
        savings = summary["budget_by_category"].get("ahorro", 0) / 100

        total_categorized = essentials + wants + savings

        if total_categorized > 0:
            essentials_pct = essentials / total_income * 100
            wants_pct = wants / total_income * 100
            savings_pct = savings / total_income * 100

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric(
                    "Necesidades (fijos)",
                    f"{essentials_pct:.0f}%",
                    delta=f"{essentials_pct - 50:+.0f}% vs ideal (50%)",
                )

            with col2:
                st.metric(
                    "Deseos (variables)",
                    f"{wants_pct:.0f}%",
                    delta=f"{wants_pct - 30:+.0f}% vs ideal (30%)",
                )

            with col3:
                st.metric(
                    "Ahorro",
                    f"{savings_pct:.0f}%",
                    delta=f"{savings_pct - 20:+.0f}% vs ideal (20%)",
                )

# ====== FOOTER ======
st.divider()
st.caption("💻 Finanzas Pro v0.1 - Gestión de finanzas compartidas")
