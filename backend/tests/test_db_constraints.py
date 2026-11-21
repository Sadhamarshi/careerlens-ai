
import os
from uuid import uuid4

import pytest
from sqlalchemy import URL, create_engine, delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Profile, User


@pytest.fixture(scope="module")
def test_engine():
    """Connect only to the dedicated test database."""

    if (
        os.environ.get("DB_NAME") != "careerlens_test_db"
        or settings.db_name != "careerlens_test_db"
    ):
        pytest.fail(
            "Database tests require DB_NAME=careerlens_test_db. "
            "Refusing to use the development database.",
            pytrace=False,
        )

    url = URL.create(
        drivername="postgresql+psycopg",
        username=settings.db_user,
        password=settings.db_password.get_secret_value(),
        host=settings.db_host,
        port=settings.db_port,
        database=settings.db_name,
    )

    engine = create_engine(url, pool_pre_ping=True)

    try:
        with engine.connect() as connection:
            actual_db = connection.execute(
                select(func.current_database())
            ).scalar_one()

            assert actual_db == "careerlens_test_db"

        yield engine

    finally:
        engine.dispose()


@pytest.fixture
def db_session(test_engine):
    """Roll back all database changes after each test."""

    with test_engine.connect() as connection:
        transaction = connection.begin()

        try:
            with Session(
                bind=connection,
                join_transaction_mode="create_savepoint",
            ) as session:
                yield session
        finally:
            transaction.rollback()


def create_test_user(db_session, email=None):
    user = User(
        email=email or f"{uuid4().hex}@example.com",
        password_hash="test-only-not-a-real-password-hash",
    )

    db_session.add(user)
    db_session.flush()

    return user


def test_user_can_be_created(db_session):
    user = create_test_user(
        db_session,
        "candidate@example.com",
    )

    assert user.id is not None
    assert user.email == "candidate@example.com"
    assert user.is_active is True


def test_duplicate_email_case_insensitive(db_session):
    create_test_user(
        db_session,
        "Candidate@Example.com",
    )

    duplicate = User(
        email="candidate@example.com",
        password_hash="test-only",
    )

    db_session.add(duplicate)

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_profile_requires_existing_user(db_session):
    profile = Profile(
        user_id=uuid4(),
        target_role="AI Engineer",
    )

    db_session.add(profile)

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_user_cannot_have_multiple_profiles(db_session):
    user = create_test_user(db_session)

    first_profile = Profile(
        user_id=user.id,
        target_role="Data Scientist",
    )

    db_session.add(first_profile)
    db_session.flush()

    second_profile = Profile(
        user_id=user.id,
        target_role="AI Engineer",
    )

    db_session.add(second_profile)

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_negative_experience_is_rejected(db_session):
    user = create_test_user(db_session)

    profile = Profile(
        user_id=user.id,
        years_experience=-2,
    )

    db_session.add(profile)

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_deleting_user_cascades_to_profile(db_session):
    user = create_test_user(db_session)

    profile = Profile(
        user_id=user.id,
        target_role="ML Engineer",
        years_experience=2,
    )

    db_session.add(profile)
    db_session.flush()

    count_before = db_session.scalar(
        select(func.count())
        .select_from(Profile)
        .where(Profile.user_id == user.id)
    )

    assert count_before == 1

    # Execute SQL DELETE directly, bypassing ORM cascades.
    db_session.execute(
        delete(User).where(User.id == user.id)
    )

    count_after = db_session.scalar(
        select(func.count())
        .select_from(Profile)
        .where(Profile.user_id == user.id)
    )

    assert count_after == 0
def test_repository_creates_and_finds_user(db_session):
    from app.repositories.user_repository import (
        create_user,
        get_user_by_email,
    )

    user = create_user(
        db_session,
        email="Candidate@Example.COM",
        password_hash="test-only-hash",
    )

    found = get_user_by_email(
        db_session,
        "CANDIDATE@example.com",
    )

    assert user.id is not None
    assert user.email == "candidate@example.com"
    assert found is not None
    assert found.id == user.id


def test_repository_returns_none_for_missing_user(db_session):
    from app.repositories.user_repository import (
        get_user_by_email,
    )

    result = get_user_by_email(
        db_session,
        "missing-user@example.com",
    )

    assert result is None