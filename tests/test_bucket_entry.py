from datetime import datetime

import pytest

from src.models.bucket_entry import BucketEntry


# ====================================================
# FIXTURES
# ====================================================
@pytest.fixture
def positive_entry():
    return BucketEntry(member_name="default", amount_cents=30000)


@pytest.fixture
def negative_entry():
    return BucketEntry(member_name="default", amount_cents=-20000)


# ====================================================
# TESTS: Entry creation
# ====================================================
def test_entry_with_positive_amount_stores_fields_correctly(positive_entry):
    assert positive_entry.amount_cents == 30000
    assert positive_entry.member_name == "default"


def test_entry_with_negative_amount_stores_fields_correctly(negative_entry):
    assert negative_entry.amount_cents == -20000
    assert negative_entry.member_name == "default"


def test_entry_date_defaults_to_creation_time():
    before_first = datetime.now()
    first = BucketEntry(amount_cents=15000, member_name="default")
    after_first = datetime.now()

    assert before_first <= first.date <= after_first


# ====================================================
# Validaciones (__post_init__)
# ====================================================
def test_zero_amount_entry_raises_error():

    with pytest.raises(ValueError, match="amount_cents no puede ser 0"):
        zero_entry = BucketEntry(amount_cents=0, member_name="default")


def test_date_cant_be_future():
    specific = datetime(2027, 3, 15, 14, 30)
    with pytest.raises(ValueError, match="La fecha no puede ser futura"):
        zero_entry = BucketEntry(amount_cents=50000, member_name="default", date=specific)


def test_name_cant_be_empty():

    with pytest.raises(ValueError, match="Nombre no puede estar vacío"):
        empty_name = BucketEntry(amount_cents=15000, member_name="")


