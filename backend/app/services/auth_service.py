from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User
from app.repositories.user_repository import create_user
from app.schemas.auth import RegisterRequest


class DuplicateEmailError(Exception):
    """Raised when an email is already registered."""


def register_user(
    db: Session,
    data: RegisterRequest,
) -> User:
    password_hash = hash_password(
        data.password.get_secret_value()
    )

    try:
        user = create_user(
            db,
            email=str(data.email),
            password_hash=password_hash,
        )

        db.commit()

    except IntegrityError as exc:
        db.rollback()

        # PostgreSQL unique constraint violation
        is_email_duplicate = (
            getattr(exc.orig, "sqlstate", None) == "23505"
            and getattr(
                getattr(exc.orig, "diag", None),
                "constraint_name",
                None,
            ) == "uq_users_email_ci"
        )

        if is_email_duplicate:
            raise DuplicateEmailError() from None

        raise

    db.refresh(user)
    return user