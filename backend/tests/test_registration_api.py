import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import database_url, get_db
from app.core.security import verify_password
from app.main import app
from app.models.user import User


@pytest.fixture
def registration_client():
    if (
        os.environ.get("DB_NAME") != "careerlens_test_db"
        or settings.db_name != "careerlens_test_db"
    ):
        pytest.fail(
            "Registration tests require careerlens_test_db",
            pytrace=False,
        )

    engine = create_engine(database_url)

    try:
        with engine.connect() as connection:
            transaction = connection.begin()

            actual_db = connection.execute(
                text("SELECT current_database()")
            ).scalar_one()

            assert actual_db == "careerlens_test_db"

            with Session(
                bind=connection,
                join_transaction_mode="create_savepoint",
            ) as session:

                def override_get_db():
                    yield session

                app.dependency_overrides[get_db] = override_get_db

                try:
                    with TestClient(app) as client:
                        yield client, session

                finally:
                    app.dependency_overrides.pop(
                        get_db, None
                    )

            transaction.rollback()

    finally:
        engine.dispose()


def test_registration_success(registration_client):
    client, session = registration_client

    password = "TestPassword123!"

    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "Candidate@Example.com",
            "password": password,
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["email"] == "candidate@example.com"
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data
    assert "password_hash" not in data
    assert "password" not in data

    user = session.scalar(
        select(User).where(
            User.email == "candidate@example.com"
        )
    )

    assert user is not None
    assert user.password_hash != password
    assert verify_password(password, user.password_hash)


def test_duplicate_registration(registration_client):
    client, session = registration_client

    first = client.post(
        "/api/v1/auth/register",
        json={
            "email": "duplicate@example.com",
            "password": "TestPassword123!",
        },
    )

    second = client.post(
        "/api/v1/auth/register",
        json={
            "email": "DUPLICATE@example.com",
            "password": "AnotherPassword123!",
        },
    )

    assert first.status_code == 201
    assert second.status_code == 409


def test_invalid_registration(registration_client):
    client, session = registration_client

    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "invalid-email",
            "password": "short",
        },
    )

    assert response.status_code == 422


def test_registration_rejects_extra_fields(
    registration_client,
):
    client, session = registration_client

    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "candidate@example.com",
            "password": "TestPassword123!",
            "is_active": True,
        },
    )

    assert response.status_code == 422