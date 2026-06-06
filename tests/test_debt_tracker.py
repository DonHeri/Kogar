import pytest

from src.models.debt_tracker import DebtTracker


@pytest.fixture
def tracker():
    t = DebtTracker()
    t.create_account("amanda")
    t.create_account("heri")
    return t


def test_create_account_adds_member(tracker):
    """create_account crea una cuenta con total pagado 0"""
    assert tracker.get_total_paid("amanda") == 0


def test_create_account_idempotent(tracker):
    tracker.create_account("amanda")  # segunda vez, no lanza ni resetea
    tracker.pay("amanda", 1000)
    tracker.create_account("amanda")
    assert tracker.get_total_paid("amanda") == 1000


def test_pay_delegates_to_account(tracker):
    """pay() registra el pago en la cuenta del miembro"""
    tracker.pay("amanda", 5000)
    assert tracker.get_total_paid("amanda") == 5000


def test_pay_accumulates_across_calls(tracker):
    """Pagos sucesivos se acumulan en el total"""
    tracker.pay("amanda", 3000)
    tracker.pay("amanda", 2000)
    assert tracker.get_total_paid("amanda") == 5000


def test_pay_nonexistent_member_raises(tracker):
    """pay() lanza ValueError si el miembro no tiene cuenta"""
    with pytest.raises(ValueError):
        tracker.pay("fantasma", 1000)


def test_get_total_paid_nonexistent_raises(tracker):
    """get_total_paid() lanza ValueError si el miembro no tiene cuenta"""
    with pytest.raises(ValueError):
        tracker.get_total_paid("fantasma")


def test_get_member_summary_structure(tracker):
    """get_member_summary() retorna dict con total_paid, history y actual_month"""
    tracker.pay("amanda", 5000)
    summary = tracker.get_member_summary("amanda")
    assert "total_paid" in summary
    assert "history" in summary
    assert "actual_month" in summary
    assert summary["total_paid"] == 5000


def test_get_history_returns_list(tracker):
    """get_history() retorna lista con los pagos registrados"""
    tracker.pay("heri", 2000)
    history = tracker.get_history("heri")
    assert len(history) == 1


def test_get_history_nonexistent_raises(tracker):
    """get_history() lanza ValueError si el miembro no tiene cuenta"""
    with pytest.raises(ValueError):
        tracker.get_history("fantasma")


def test_accounts_are_independent(tracker):
    """Pagos de un miembro no afectan a los de otro"""
    tracker.pay("amanda", 10000)
    tracker.pay("heri", 3000)
    assert tracker.get_total_paid("amanda") == 10000
    assert tracker.get_total_paid("heri") == 3000
