from sqlalchemy import UniqueConstraint

from app.models import AuthSession
from app.models.base import Base


def test_auth_session_registered():
    assert "auth_sessions" in Base.metadata.tables


def test_auth_session_required_columns():
    columns = AuthSession.__table__.columns

    assert columns["user_id"].nullable is False
    assert columns["token_hash"].nullable is False
    assert columns["csrf_token_hash"].nullable is False
    assert columns["expires_at"].nullable is False
    assert columns["revoked_at"].nullable is True


def test_auth_session_user_foreign_key():
    foreign_keys = (
        AuthSession.__table__.c.user_id.foreign_keys
    )

    assert len(foreign_keys) == 1

    foreign_key = next(iter(foreign_keys))

    assert foreign_key.target_fullname == "users.id"
    assert foreign_key.ondelete == "CASCADE"


def test_auth_session_token_is_unique():
    constraints = AuthSession.__table__.constraints

    unique_columns = [
        {column.name for column in constraint.columns}
        for constraint in constraints
        if isinstance(constraint, UniqueConstraint)
    ]

    assert {"token_hash"} in unique_columns