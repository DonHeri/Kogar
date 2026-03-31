import pytest
from datetime import datetime
from src.models.saving_account import SavingAccount
from src.models.saving_entry import SavingEntry
from src.models.constants import SavingScope
from src.utils.currency import to_cents

# ====================================================
# FIXTURES
# ====================================================


@pytest.fixture
def account():
    """Cuenta de ahorro vacía para el miembro Amanda"""
    return SavingAccount("Amanda")


@pytest.fixture
def account_with_funds(account):
    """Cuenta con fondos: 100€ PERSONAL y 50€ SHARED"""
    account.deposit(
        destination=SavingScope.PERSONAL,
        amount_cents=to_cents(100.0),
        description="Ahorro inicial personal",
    )
    account.deposit(
        destination=SavingScope.SHARED,
        amount_cents=to_cents(50.0),
        description="Fondo común",
    )
    return account


# ====================================================
# TESTS: Creación y Validaciones de Inicialización
# ====================================================


def test_creation_valid_account_initializes_correctly():
    """Test: Crear cuenta válida inicializa nombre y lista vacía"""
    acc = SavingAccount("Heri")

    assert acc.member_name == "Heri"
    assert len(acc._entries) == 0


def test_creation_empty_name_raises_error():
    """Test: Crear cuenta con string vacío lanza ValueError"""
    with pytest.raises(ValueError, match="member_name no puede estar vacío"):
        SavingAccount("")


def test_creation_whitespace_name_raises_error():
    """Test: Crear cuenta con solo espacios lanza ValueError"""
    with pytest.raises(ValueError, match="member_name no puede estar vacío"):
        SavingAccount("   ")


# ====================================================
# TESTS: deposit
# ====================================================


def test_deposit_adds_entry_with_correct_data(account):
    """Test: Realizar un depósito agrega un SavingEntry correcto"""
    account.deposit(
        destination=SavingScope.PERSONAL,
        amount_cents=to_cents(150.0),
        description="Regalo cumpleaños",
        date=datetime(2026, 1, 15),
    )

    entries = account.get_history()
    assert len(entries) == 1
    assert entries[0].amount_cents == 15000
    assert entries[0].destination == SavingScope.PERSONAL
    assert entries[0].description == "regalo cumpleaños"  # stored stripped and lowered
    assert entries[0].date == datetime(2026, 1, 15)


def test_deposit_normalizes_description(account):
    """Test: El depósito normaliza la descripción (strip y minúsculas)"""
    account.deposit(
        destination=SavingScope.SHARED,
        amount_cents=to_cents(20.0),
        description="   BONUS EXTRA   ",
    )

    entries = account.get_history()
    assert entries[0].description == "bonus extra"


def test_deposit_without_date_uses_current_time(account):
    """Test: Depósito sin fecha especificada usa datetime.now()"""
    before = datetime.now()
    account.deposit(SavingScope.PERSONAL, to_cents(10.0))
    after = datetime.now()

    entry_date = account.get_history()[0].date
    assert before <= entry_date <= after


def test_deposit_zero_amount_raises_error(account):
    """Test: Depositar 0 lanza ValueError"""
    with pytest.raises(ValueError, match="amount_cents debe ser distinto a 0"):
        account.deposit(SavingScope.PERSONAL, 0)


def test_deposit_negative_amount_raises_error(account):
    """Test: Depositar monto negativo lanza ValueError"""
    with pytest.raises(ValueError, match="amount_cents debe ser distinto a 0"):
        account.deposit(SavingScope.PERSONAL, -5000)


def test_deposit_float_amount_raises_error(account):
    """Test: Depositar un float lanza ValueError"""
    with pytest.raises(ValueError, match="amount_cents debe ser entero"):
        account.deposit(SavingScope.PERSONAL, 15.5)


# ====================================================
# TESTS: withdraw
# ====================================================


def test_withdraw_adds_negative_entry_and_reduces_balance(account_with_funds):
    """Test: Retirar fondos agrega un entry negativo y reduce saldo"""
    # account_with_funds tiene 100€ (10000 céntimos) PERSONAL
    account_with_funds.withdraw(
        destination=SavingScope.PERSONAL,
        amount_cents=to_cents(40.0),
        description="Compra capricho",
        date=datetime(2026, 2, 10),
    )

    entries = account_with_funds.get_history()
    assert len(entries) == 3  # 2 depósitos iniciales + 1 retiro
    assert entries[-1].amount_cents == -4000
    assert entries[-1].destination == SavingScope.PERSONAL
    assert entries[-1].description == "compra capricho"
    assert account_with_funds.balance_personal == 6000  # 100€ - 40€ = 60€


def test_withdraw_insufficient_funds_raises_error(account_with_funds):
    """Test: Retirar más fondos de los disponibles lanza ValueError exacto"""
    # account_with_funds tiene 50€ (5000 céntimos) SHARED
    with pytest.raises(
        ValueError,
        match=f"Saldo insuficiente en {SavingScope.SHARED.value}. Disponible: 5000 céntimos",
    ):
        account_with_funds.withdraw(
            destination=SavingScope.SHARED, amount_cents=to_cents(60.0)
        )


def test_withdraw_does_not_mix_destinations(account_with_funds):
    """Test: Retiro evalúa solo el saldo del destino correspondiente"""
    # Tiene 100€ PERSONAL y 50€ SHARED. Total = 150€.
    # Intentar retirar 80€ SHARED debe fallar aunque el balance total lo cubra.
    with pytest.raises(
        ValueError,
        match=f"Saldo insuficiente en {SavingScope.SHARED.value}. Disponible: 5000 céntimos",
    ):
        account_with_funds.withdraw(
            destination=SavingScope.SHARED, amount_cents=to_cents(80.0)
        )


def test_withdraw_zero_amount_raises_error(account_with_funds):
    """Test: Retirar 0 lanza ValueError"""
    with pytest.raises(ValueError, match="amount_cents debe ser distinto a 0"):
        account_with_funds.withdraw(SavingScope.PERSONAL, 0)


# ====================================================
# TESTS: Properties (Balances)
# ====================================================


def test_balance_total_sums_all_destinations(account_with_funds):
    """Test: balance_total suma ahorros de todas las destinaciones"""
    # 100€ + 50€ = 150€ = 15000 céntimos
    assert account_with_funds.balance_total == 15000


def test_balance_personal_sums_only_personal(account_with_funds):
    """Test: balance_personal suma únicamente ahorros PERSONAL"""
    # 100€ = 10000 céntimos
    assert account_with_funds.balance_personal == 10000


def test_balance_shared_sums_only_shared(account_with_funds):
    """Test: balance_shared suma únicamente ahorros SHARED"""
    # 50€ = 5000 céntimos
    assert account_with_funds.balance_shared == 5000


def test_balances_empty_account_returns_zero(account):
    """Test: Todas las properties de balance devuelven 0 si no hay entries"""
    assert account.balance_total == 0
    assert account.balance_personal == 0
    assert account.balance_shared == 0

# ====================================================
# TESTS: get_history
# ====================================================


def test_get_history_returns_copy_of_entries(account_with_funds):
    """Test: get_history devuelve una copia que no muta la lista original"""
    history = account_with_funds.get_history()

    # Mutar la copia devuelta
    history.clear()

    # La lista original no debe verse afectada
    assert len(account_with_funds._entries) == 2


def test_get_history_empty_returns_empty_list(account):
    """Test: get_history devuelve lista vacía si no hay movimientos"""
    history = account.get_history()
    assert history == []
    assert isinstance(history, list)


# ====================================================
# TESTS: get_monthly_summary
# ====================================================


def test_get_monthly_summary_filters_correctly_by_month_and_year(account):
    """Test: El resumen mensual filtra por mes y año exactos"""
    # Mes actual (evaluado - Enero 2026 para estar en un pasado seguro)
    account.deposit(
        SavingScope.PERSONAL, to_cents(100.0), date=datetime(2026, 1, 15)
    )
    account.deposit(
        SavingScope.SHARED, to_cents(50.0), date=datetime(2026, 1, 20)
    )
    account.withdraw(
        SavingScope.PERSONAL, to_cents(20.0), date=datetime(2026, 1, 25)
    )

    # Otros meses / años (no deben contar - usamos Febrero 2026 y 2025)
    account.deposit(
        SavingScope.PERSONAL, to_cents(200.0), date=datetime(2026, 2, 10)
    )
    account.deposit(
        SavingScope.SHARED, to_cents(500.0), date=datetime(2025, 1, 15)
    )

    # Evaluamos enero
    summary = account.get_monthly_summary(month=1, year=2026)

    assert isinstance(summary, dict)
    assert summary["personal"] == 8000  # 100€ - 20€
    assert summary["shared"] == 5000  # 50€


def test_get_monthly_summary_empty_month_returns_zeros(account_with_funds):
    """Test: Mes sin movimientos devuelve resumen con ceros"""
    # account_with_funds usa datetime.now(), así que pedimos un año muy lejano
    summary = account_with_funds.get_monthly_summary(month=1, year=1999)

    assert summary["personal"] == 0
    assert summary["shared"] == 0


# ====================================================
# TESTS: Integration
# ====================================================


def test_account_lifecycle_multiple_operations():
    """Test: Flujo completo de múltiples depósitos, retiros y consultas de balance"""
    acc = SavingAccount("Amanda")

    # 1. Depósitos iniciales
    acc.deposit(SavingScope.PERSONAL, to_cents(500.0))
    acc.deposit(SavingScope.SHARED, to_cents(300.0))

    assert acc.balance_total == 80000
    assert acc.balance_personal == 50000
    assert acc.balance_shared == 30000

    # 2. Retiros válidos
    acc.withdraw(SavingScope.PERSONAL, to_cents(150.0))
    acc.withdraw(SavingScope.SHARED, to_cents(300.0))  # Vacía el compartido

    assert acc.balance_total == 35000
    assert acc.balance_personal == 35000
    assert acc.balance_shared == 0

    # 3. Intento de retiro fallido (no afecta saldos)
    with pytest.raises(ValueError, match="Saldo insuficiente"):
        acc.withdraw(SavingScope.SHARED, to_cents(10.0))

    assert acc.balance_shared == 0
    assert (
        len(acc.get_history()) == 4
    )  # 2 depósitos + 2 retiros (el fallido no se registra)
