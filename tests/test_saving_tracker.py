import pytest
from datetime import datetime
from src.models.saving_tracker import SavingTracker
from src.models.constants import SavingDestination
from src.utils.currency import to_cents

# ====================================================
# FIXTURES
# ====================================================


@pytest.fixture
def tracker():
    """SavingTracker vacío sin cuentas"""
    return SavingTracker()


@pytest.fixture
def tracker_with_accounts(tracker):
    """Tracker con cuentas vacías para amanda y heri"""
    tracker.create_account("amanda")
    tracker.create_account("heri")
    return tracker


@pytest.fixture
def tracker_with_funds(tracker_with_accounts):
    """Tracker con cuentas y fondos mixtos (SHARED y PERSONAL)"""
    # Amanda: 100€ compartidos, 50€ personales
    tracker_with_accounts.deposit(
        "amanda",
        to_cents(100.0),
        SavingDestination.SHARED,
        "Fondo hogar",
        datetime(2026, 3, 1),
    )
    tracker_with_accounts.deposit(
        "amanda",
        to_cents(50.0),
        SavingDestination.PERSONAL,
        "Ahorro propio",
        datetime(2026, 3, 5),
    )

    # Heri: 200€ compartidos, 0€ personales
    tracker_with_accounts.deposit(
        "heri",
        to_cents(200.0),
        SavingDestination.SHARED,
        "Bono compartido",
        datetime(2026, 3, 10),
    )
    return tracker_with_accounts


# ====================================================
# TESTS: create_account
# ====================================================


def test_create_account_adds_new_member(tracker):
    """Test: Crea cuenta nueva correctamente en el tracker"""
    # Arrange & Act
    tracker.create_account("amanda")

    # Assert
    assert "amanda" in tracker._accounts
    assert tracker._accounts["amanda"].member_name == "amanda"


def test_create_account_does_not_overwrite_existing(tracker):
    """Test: Si la cuenta ya existe, no la sobreescribe (mantiene fondos)"""
    # Arrange
    tracker.create_account("amanda")
    tracker.deposit("amanda", to_cents(10.0), SavingDestination.PERSONAL)

    # Act
    tracker.create_account("amanda")  # Intento duplicado

    # Assert
    assert tracker._accounts["amanda"].balance_personal == 1000


# ====================================================
# TESTS: deposit & withdraw (Delegation)
# ====================================================


def test_deposit_delegates_to_member_account(tracker_with_accounts):
    """Test: deposit() envía los fondos a la cuenta correcta"""
    # Arrange & Act
    tracker_with_accounts.deposit(
        "amanda", to_cents(150.0), SavingDestination.SHARED, "Ingreso extra"
    )

    # Assert
    assert tracker_with_accounts._accounts["amanda"].balance_shared == 15000
    assert tracker_with_accounts._accounts["heri"].balance_total == 0


def test_withdraw_delegates_to_member_account(tracker_with_funds):
    """Test: withdraw() extrae fondos de la cuenta correcta"""
    # Arrange: amanda tiene 100€ SHARED
    # Act
    tracker_with_funds.withdraw(
        "amanda", to_cents(40.0), SavingDestination.SHARED, "Gasto imprevisto"
    )

    # Assert
    assert (
        tracker_with_funds._accounts["amanda"].balance_shared == 6000
    )  # 100 - 40 = 60€


def test_withdraw_raises_error_if_insufficient_funds(tracker_with_funds):
    """Test: withdraw() lanza ValueError si la cuenta no tiene fondos suficientes"""
    # Arrange & Act & Assert
    with pytest.raises(ValueError, match="Saldo insuficiente en"):
        tracker_with_funds.withdraw("amanda", to_cents(500.0), SavingDestination.SHARED)


# ====================================================
# TESTS: Queries Individuales
# ====================================================


def test_get_shared_balance_returns_only_shared_funds(tracker_with_funds):
    """Test: get_shared_balance retorna suma de destination SHARED"""
    # Arrange & Act
    balance = tracker_with_funds.get_shared_balance("amanda")

    # Assert
    assert balance == 10000  # 100€ compartidos (ignora los 50€ personales)


def test_get_history_shared_returns_only_shared_entries(tracker_with_funds):
    """Test: get_history_shared filtra entries con destination PERSONAL"""
    # Arrange & Act
    history = tracker_with_funds.get_history_shared("amanda")

    # Assert
    assert len(history) == 1
    assert history[0].destination == SavingDestination.SHARED
    assert history[0].amount_cents == 10000


def test_get_member_summary_returns_complete_structure(tracker_with_funds):
    """Test: get_member_summary retorna diccionario con balances e historial"""
    # Arrange
    now = datetime.now()
    tracker_with_funds.deposit(
        "amanda", to_cents(20.0), SavingDestination.PERSONAL, date=now
    )

    # Act
    summary = tracker_with_funds.get_member_summary("amanda")

    # Assert
    assert summary["balance_total"] == 17000  # 100€ shared + 50€ init + 20€ now
    assert summary["balance_personal"] == 7000
    assert summary["balance_shared"] == 10000
    assert isinstance(summary["history"], list)
    assert isinstance(summary["actual_month"], dict)
    assert summary["actual_month"]["personal"] >= 2000


def test_get_member_summary_raises_error_if_no_account(tracker):
    """Test: get_member_summary valida existencia de cuenta"""
    # Arrange & Act & Assert
    with pytest.raises(ValueError, match="Miembro no tiene SavingAccount en tracker"):
        tracker.get_member_summary("inexistente")


# ====================================================
# TESTS: Queries Agregadas
# ====================================================


def test_get_total_shared_sums_all_members(tracker_with_funds):
    """Test: get_total_shared suma los balances compartidos de todas las cuentas"""
    # Arrange & Act
    total = tracker_with_funds.get_total_shared()

    # Assert
    # Amanda 100€ + Heri 200€ = 300€ = 30000 céntimos
    assert total == 30000


def test_get_total_shared_empty_tracker_returns_zero(tracker):
    """Test: get_total_shared retorna 0 si no hay cuentas"""
    # Arrange & Act & Assert
    assert tracker.get_total_shared() == 0


def test_get_shared_by_month_returns_filtered_entries(tracker_with_funds):
    """Test: get_shared_by_month agrupa movimientos SHARED por mes y año"""
    # Arrange
    # Añadimos un movimiento fuera del mes objetivo (Febrero 2026, siempre en el pasado)
    tracker_with_funds.deposit(
        "amanda", to_cents(50.0), SavingDestination.SHARED, date=datetime(2026, 2, 1)
    )

    # Act
    # Buscamos movimientos de Marzo 2026 (los iniciales del fixture, que son de inicios de mes)
    march_data = tracker_with_funds.get_shared_by_month(3, 2026)

    # Assert
    assert len(march_data["amanda"]) == 1
    assert march_data["amanda"][0].amount_cents == 10000
    assert len(march_data["heri"]) == 1
    assert march_data["heri"][0].amount_cents == 20000


def test_get_shared_by_month_includes_empty_lists_for_no_activity(tracker_with_funds):
    """Test: Miembros sin actividad en el mes aparecen con lista vacía"""
    # Arrange & Act
    # Buscamos un mes sin movimientos
    empty_month_data = tracker_with_funds.get_shared_by_month(12, 2026)

    # Assert
    assert "amanda" in empty_month_data
    assert empty_month_data["amanda"] == []
    assert "heri" in empty_month_data
    assert empty_month_data["heri"] == []


def test_get_total_shared_history_returns_dict_of_shared_entries(tracker_with_funds):
    """Test: get_total_shared_history agrupa historial de todos los miembros"""
    # Arrange & Act
    history = tracker_with_funds.get_total_shared_history()

    # Assert
    assert "amanda" in history
    assert "heri" in history
    assert len(history["amanda"]) == 1
    assert history["amanda"][0].destination == SavingDestination.SHARED
    assert len(history["heri"]) == 1


# ====================================================
# TESTS: Integration
# ====================================================


def test_integration_saving_tracker_flow(tracker):
    """Test: Flujo completo de gestión de ahorros compartidos y personales"""
    # 1. Registro
    tracker.create_account("amanda")
    tracker.create_account("heri")

    # 2. Aportaciones de inicio de mes
    tracker.deposit("amanda", to_cents(300.0), SavingDestination.SHARED, "Aporte fijo")
    tracker.deposit("heri", to_cents(300.0), SavingDestination.SHARED, "Aporte fijo")
    tracker.deposit(
        "amanda", to_cents(100.0), SavingDestination.PERSONAL, "Ahorro Amanda"
    )

    # Verificaciones parciales
    assert tracker.get_total_shared() == 60000  # 600€
    assert tracker.get_shared_balance("amanda") == 30000  # 300€

    # 3. Retiro para cubrir un gasto del hogar
    tracker.withdraw(
        "amanda", to_cents(50.0), SavingDestination.SHARED, "Compra urgente"
    )

    # Verificaciones finales
    assert tracker.get_total_shared() == 55000  # 550€
    assert tracker._accounts["amanda"].balance_personal == 10000  # 100€ (intacto)

    # 4. Extracción de resúmenes
    amanda_summary = tracker.get_member_summary("amanda")
    assert amanda_summary["balance_shared"] == 25000  # 300 - 50
    assert len(amanda_summary["history"]) == 3  # 2 depósitos + 1 retiro
