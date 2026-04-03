import pytest
from uuid import UUID
from datetime import datetime
from src.models.constants import SavingScope
from src.models.bucket_tracker import BucketTracker
from src.models.saving_bucket import SavingBucket


# ====================================================
# FIXTURES
# ====================================================
@pytest.fixture
def tracker():
    return BucketTracker()


@pytest.fixture
def bucket_shared_trip_to_japan():
    return {
        "bucket_name": "Viaje a Japón",
        "deadline": datetime(2027, 4, 23),
        "goal_cents": 280000,
        "scope": SavingScope.SHARED,
        "owners": ["amanda", "heri"],
    }


@pytest.fixture
def bucket_shared_emergency_fund():
    return {
        "bucket_name": "Fondo de emergencia",
        "goal_cents": 600000,
        "scope": SavingScope.SHARED,
        "owners": ["amanda", "heri"],
        "description": "3 meses de gastos fijos cubiertos",
    }


@pytest.fixture
def bucket_personal_new_mac():
    return {
        "bucket_name": "MacBook Pro",
        "deadline": datetime(2026, 11, 1),
        "goal_cents": 220000,
        "scope": SavingScope.PERSONAL,
        "owners": ["heri"],
    }


@pytest.fixture
def bucket_personal_amanda_course():
    return {
        "bucket_name": "Curso de diseño UX",
        "goal_cents": 45000,
        "scope": SavingScope.PERSONAL,
        "owners": ["amanda"],
        "description": "Máster online",
    }


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
        tracker.add_bucket(**bucket)


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

    id_emergency_fund = tracker.add_bucket(**bucket_shared_emergency_fund)

    assert isinstance(id_emergency_fund, UUID)


def test_add_bucket_stores_bucket(tracker, bucket_personal_amanda_course):
    id_course = tracker.add_bucket(**bucket_personal_amanda_course)

    assert len(tracker.buckets) == 1


def test_add_bucket_uses_bucket_id_as_key(): ...


def test_get_all_buckets_returns_copy(): ...


def test_get_all_buckets_empty_tracker(): ...


def test_get_bucket_by_id_returns_correct_bucket(): ...


def test_get_bucket_by_id_raises_if_not_found(): ...


def test_get_bucket_by_member_returns_matching_buckets(): ...


def test_get_bucket_by_member_returns_empty_if_no_match(): ...


def test_deposit_delegates_to_bucket(): ...


def test_deposit_raises_if_bucket_not_found(): ...


def test_withdraw_delegates_to_bucket(): ...


def test_withdraw_raises_if_insufficient_balance(): ...
