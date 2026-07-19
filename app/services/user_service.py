from sqlalchemy.orm import Session

from app.models.user import User
from app.services.auth_service import hash_password, verify_password


def get_user_by_email(db: Session, email: str):
    return (
        db.query(User)
        .filter(User.email == email.lower())
        .first()
    )


def get_user_by_id(db: Session, user_id: int):
    return (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )


def create_user(
    db: Session,
    email: str,
    name: str,
    password: str,
):
    user = User(
        email=email.lower(),
        name=name,
        hashed_password=hash_password(password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(
    db: Session,
    email: str,
    password: str,
):
    user = get_user_by_email(db, email)
    if not user:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user
