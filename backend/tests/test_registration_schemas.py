from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.auth import RegisterRequest, UserResponse


def test_valid_registration():
    request = RegisterRequest(
        email="Candidate@Example.COM",
        password="ExamplePassword123!",
    )

    assert request.email == "candidate@example.com"


def test_invalid_email_rejected():
    with pytest.raises(ValidationError):
        RegisterRequest(
            email="not-an-email",
            password="ExamplePassword123!",
        )


def test_short_password_rejected():
    with pytest.raises(ValidationError):
        RegisterRequest(
            email="candidate@example.com",
            password="short",
        )


def test_extra_fields_rejected():
    with pytest.raises(ValidationError):
        RegisterRequest.model_validate({
            "email": "candidate@example.com",
            "password": "ExamplePassword123!",
            "is_active": True,
        })


def test_user_response_excludes_password_hash():
    user = SimpleNamespace(
        id=uuid4(),
        email="candidate@example.com",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        password_hash="fictional-hash",
    )

    response = UserResponse.model_validate(user)

    assert "password_hash" not in response.model_dump()
    assert response.email == "candidate@example.com"