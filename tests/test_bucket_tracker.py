from datetime import datetime
from uuid import UUID

import pytest

from src.models.bucket_tracker import BucketTracker
from src.models.constants import SavingScope
from src.models.saving_bucket import SavingBucket


# ====================================================
# FIXTURES
# ====================================================
@pytest.fixture
def tracker():
    return BucketTracker()


@pytest.fixture
def bucket_shared_trip_to_japan():
    return SavingBucket(
        bucket_name="Viaje a Japón",
        deadline=datetime(2027, 4, 23),
        goal_cents=280000,
        scope=SavingScope.SHARED,
        owners=["amanda", "heri"],
    )


@pytest.fixture
def bucket_shared_emergency_fund():
    return SavingBucket(
        bucket_name="Fondo de emergencia",
        goal_cents=600000,
        scope=SavingScope.SHARED,
        owners=["amanda", "heri"],
        description="3 meses de gastos fijos cubiertos",
    )


@pytest.fixture
def bucket_personal_new_mac():
    return SavingBucket(
        bucket_name="MacBook Pro",
        deadline=datetime(2026, 11, 1),
        goal_cents=220000,
        scope=SavingScope.PERSONAL,
        owners=["heri"],
    )


@pytest.fixture
def bucket_personal_amanda_course():
    return SavingBucket(
        bucket_name="Curso de diseño UX",
        goal_cents=45000,
        scope=SavingScope.PERSONAL,
        owners=["amanda"],
        description="Máster online",
    )


@pytest.fixture
def tracker_with_buckets(
    tracker,
    bucket_shared_trip_to_japan,
    bucket_shared_emergency_fund,
    bucket_personal_new_mac,
    bucket_personal_amanda_course,
):

    for bucket in [
        bucket_shared_trip_to_japan,
        bucket_shared_emergency_fund,
        bucket_personal_new_mac,
        bucket_personal_amanda_course,
    ]:
        tracker.add_bucket(bucket)

    return tracker


# ====================================================
# TESTS: Tracker creation
# ====================================================


def tests_bucket_tracker_creation_valid():
    """Test: Crear un Bucket Tracker válido"""
    tracker = BucketTracker()

    assert isinstance(tracker.buckets, dict)
    assert len(tracker.buckets) == 0


# ====================================================
# TESTS: create_add_new_bucket
# ====================================================


def test_add_bucket_returns_uuid(tracker, bucket_shared_emergency_fund):

    id_emergency_fund = tracker.add_bucket(bucket_shared_emergency_fund)

    assert isinstance(id_emergency_fund, UUID)


def test_add_bucket_stores_bucket(tracker, bucket_personal_amanda_course):
    id_course = tracker.add_bucket(bucket_personal_amanda_course)

    assert len(tracker.buckets) == 1
    assert "amanda" in tracker.buckets[id_course].owners


def test_add_bucket_uses_bucket_id_as_key(tracker, bucket_shared_emergency_fund):
    """El UUID devuelto por add_bucket coincide con la clave en el dict"""
    bucket_id = tracker.add_bucket(bucket_shared_emergency_fund)

    assert bucket_id in tracker.buckets
    assert tracker.buckets[bucket_id].id == bucket_id


def test_get_all_buckets_returns_copy(tracker_with_buckets):
    copy = tracker_with_buckets.get_all_buckets()

    assert len(copy) == 4
    copy.clear()
    assert len(tracker_with_buckets.buckets) == 4


def test_get_all_buckets_empty_tracker(tracker):
    empty_copy = tracker.get_all_buckets()

    assert len(empty_copy) == 0
    assert isinstance(empty_copy, dict)


# ====================================================
# TESTS: get_bucket_by_id
# ====================================================


def test_get_bucket_by_id_returns_correct_bucket(tracker, bucket_personal_new_mac):
    bucket_id = tracker.add_bucket(bucket_personal_new_mac)

    bucket = tracker.get_bucket_by_id(bucket_id)

    assert bucket.id == bucket_id
    assert bucket.bucket_name == "MacBook Pro"


def test_get_bucket_by_id_raises_if_not_found(tracker):
    from uuid import uuid4

    fake_id = uuid4()

    with pytest.raises(ValueError, match="no existe"):
        tracker.get_bucket_by_id(fake_id)


# ====================================================
# TESTS: get_bucket_by_member
# ====================================================


def test_get_bucket_by_member_returns_matching_buckets(tracker_with_buckets):
    """amanda participa en 3 de los 4 buckets"""
    result = tracker_with_buckets.get_bucket_by_member("amanda")

    assert len(result) == 3
    for bucket in result.values():
        assert "amanda" in bucket.owners


def test_get_bucket_by_member_returns_empty_if_no_match(tracker_with_buckets):
    result = tracker_with_buckets.get_bucket_by_member("miembro_inexistente")

    assert result == {}


# ====================================================
# TESTS: deposit
# ====================================================


def test_deposit_delegates_to_bucket(tracker, bucket_shared_emergency_fund):
    bucket_id = tracker.add_bucket(bucket_shared_emergency_fund)

    tracker.deposit(bucket_id, 10000, "amanda")

    assert tracker.get_bucket_by_id(bucket_id).balance == 10000


def test_deposit_raises_if_bucket_not_found(tracker):
    from uuid import uuid4

    fake_id = uuid4()

    with pytest.raises(ValueError, match="no existe"):
        tracker.deposit(fake_id, 10000, "amanda")


# ====================================================
# TESTS: withdraw
# ====================================================


def test_withdraw_delegates_to_bucket(tracker, bucket_shared_emergency_fund):
    bucket_id = tracker.add_bucket(bucket_shared_emergency_fund)
    tracker.deposit(bucket_id, 10000, "amanda")

    tracker.withdraw(bucket_id, 5000, "amanda")

    assert tracker.get_bucket_by_id(bucket_id).balance == 5000


def test_withdraw_raises_if_insufficient_balance(tracker, bucket_shared_emergency_fund):
    bucket_id = tracker.add_bucket(bucket_shared_emergency_fund)
    tracker.deposit(bucket_id, 5000, "amanda")

    with pytest.raises(ValueError, match="Saldo insuficiente"):
        tracker.withdraw(bucket_id, 10000, "amanda")


# ====================================================
# TESTS: get_all_bucket
# ====================================================


def test_get_all_buckets_return_copy_all_buckets(tracker_with_buckets):
    buckets = tracker_with_buckets.get_all_buckets()
    buckets_names = [
        "Viaje a Japón",
        "Fondo de emergencia",
        "MacBook Pro",
        "Curso de diseño UX",
    ]

    for _, bucket in buckets.items():
        assert bucket.bucket_name in buckets_names


def test_get_bucket_id_returns_correct_bucket(
    tracker, bucket_personal_new_mac, bucket_shared_emergency_fund
):
    id_mac = tracker.add_bucket(bucket_personal_new_mac)
    id_emergency_fund = tracker.add_bucket(bucket_shared_emergency_fund)

    bucket_mac = tracker.get_bucket_by_id(id_mac)
    bucket_emergency_fund = tracker.get_bucket_by_id(id_emergency_fund)

    assert bucket_mac.bucket_name == "MacBook Pro"
    assert bucket_emergency_fund.bucket_name == "Fondo de emergencia"


def test_get_bucket_by_member_heri_has_three_buckets(tracker_with_buckets):
    """heri participa en 3 de los 4 buckets"""
    result = tracker_with_buckets.get_bucket_by_member("heri")

    assert len(result) == 3
    for bucket in result.values():
        assert "heri" in bucket.owners


# ====================================================
# TESTS: withdraw - bucket not found
# ====================================================


def test_withdraw_raises_if_bucket_not_found(tracker):
    from uuid import uuid4

    fake_id = uuid4()

    with pytest.raises(ValueError, match="no existe"):
        tracker.withdraw(fake_id, 5000, "amanda")


# ====================================================
# TESTS: deposit / withdraw with date
# ====================================================


def test_deposit_with_date(tracker, bucket_shared_emergency_fund):
    bucket_id = tracker.add_bucket(bucket_shared_emergency_fund)
    date = datetime(2026, 1, 15)

    tracker.deposit(bucket_id, 5000, "amanda", date=date)

    bucket = tracker.get_bucket_by_id(bucket_id)
    assert bucket.balance == 5000
    assert bucket._entries[0].date == date


def test_withdraw_with_date(tracker, bucket_shared_emergency_fund):
    bucket_id = tracker.add_bucket(bucket_shared_emergency_fund)
    date_dep = datetime(2026, 1, 10)
    date_wit = datetime(2026, 2, 5)

    tracker.deposit(bucket_id, 10000, "amanda", date=date_dep)
    tracker.withdraw(bucket_id, 3000, "amanda", date=date_wit)

    bucket = tracker.get_bucket_by_id(bucket_id)
    assert bucket.balance == 7000
    assert bucket._entries[1].date == date_wit
