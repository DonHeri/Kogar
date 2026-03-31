import pytest
from datetime import datetime
from src.models.saving_entry import SavingEntry
from src.models.constants import SavingScope


@pytest.fixture
def positive_shared_entry():
    return SavingEntry(
        amount_cents=15000,
        destination=SavingScope.SHARED,
        description="ahorro compartido",
    )


@pytest.fixture
def negative_personal_entry():
    return SavingEntry(
        amount_cents=-25000,
        destination=SavingScope.PERSONAL,
        description="ahorro personal",
    )


# ====== Creación válida ======
def test_entry_with_positive_amount_stores_fields_correctly(positive_shared_entry):

    assert positive_shared_entry.amount_cents == 15000
    assert positive_shared_entry.destination == SavingScope.SHARED
    assert positive_shared_entry.description == "ahorro compartido"


def test_entry_with_negative_amount_is_valid(negative_personal_entry):
    assert negative_personal_entry.amount_cents == -25000
    assert negative_personal_entry.destination == SavingScope.PERSONAL
    assert negative_personal_entry.description == "ahorro personal"


def test_entry_date_defaults_to_creation_time():
    before_first = datetime.now()
    first = SavingEntry(
        amount_cents=15000,
        destination=SavingScope.SHARED,
        description="ahorro compartido",
    )
    after_first = datetime.now()

    assert before_first <= first.date <= after_first


# ====== Validaciones (__post_init__) ======
def test_zero_amount_entry_raises_error():

    with pytest.raises(ValueError, match="amount_cents no puede ser 0"):
        zero_entry = SavingEntry(
            amount_cents=0,
            destination=SavingScope.SHARED,
            description="zero entry",
        )


def test_date_cant_be_future():
    specific = datetime(2027, 3, 15, 14, 30)
    with pytest.raises(ValueError, match="La fecha no puede ser futura"):
        zero_entry = SavingEntry(
            amount_cents=16000,
            destination=SavingScope.SHARED,
            description="zero entry",
            date=specific,
        )
