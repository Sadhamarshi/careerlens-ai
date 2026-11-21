from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import User


def get_user_by_email(
    db: Session,
    email: str,
) -> User | None:
    normalized_email = email.strip().lower()

    statement = select(User).where(
        func.lower(User.email) == normalized_email
    )

    return db.scalar(statement)


def create_user(
    db: Session,
    *,
    email: str,
    password_hash: str,
) -> User:
    user = User(
        email=email.strip().lower(),
        password_hash=password_hash,
    )

    db.add(user)
    db.flush()

    return user