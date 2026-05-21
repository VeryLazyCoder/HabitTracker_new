from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_

import app.Database.models as model
from app.Auth.security import (
    hash_password,
    verify_password
)

from app.Exceptions.exceptions import (
    UserAlreadyExistsException,
    UserNotFoundException
)


def create_user(
    context: Session,
    username: str,
    password: str,
    email: str
):

    existing_user = (
        context.query(model.User)
        .filter(
            (model.User.username == username) |
            (model.User.email == email)
        )
        .first()
    )

    if existing_user:
        raise UserAlreadyExistsException(
            "User already exists"
        )

    try:

        user = model.User(
            username=username,
            password=hash_password(password),
            email=email
        )

        context.add(user)

        context.commit()

        context.refresh(user)

        return user

    except IntegrityError:

        context.rollback()

        raise UserAlreadyExistsException(
            "User already exists"
        )

    except Exception:

        context.rollback()

        raise


def get_user_by_id(
    context: Session,
    user_id: int
):

    user = (
        context.query(model.User)
        .filter(model.User.id == user_id)
        .first()
    )

    if not user:
        raise UserNotFoundException(
            "User not found"
        )

    return user


def get_user_by_email(
    context: Session,
    email: str
):

    user = (
        context.query(model.User)
        .filter(model.User.email == email)
        .first()
    )

    if not user:
        raise UserNotFoundException(
            "User not found"
        )

    return user


def get_user_by_login(
    context: Session,
    login: str
):

    return (
        context.query(model.User)
        .filter(
            or_(
                model.User.username == login,
                model.User.email == login
            )
        )
        .first()
    )


def authenticate_user(
    context: Session,
    login: str,
    password: str
):

    user = get_user_by_login(context, login)

    if not user:
        return None

    if not verify_password(password, user.password):
        return None

    return user
