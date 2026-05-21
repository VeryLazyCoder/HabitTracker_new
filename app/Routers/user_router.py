from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.Database.connection import get_db
from app.Schemas.user_schema import (
    UserCreate,
    UserLogin,
    UserResponse
)

from app.Services.user_service import (
    authenticate_user,
    create_user,
    get_user_by_id
)

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)


@router.post(
    "/",
    response_model=UserResponse
)
def create_new_user(
    user: UserCreate,
    db: Session = Depends(get_db)
):

    return create_user(
        db,
        username=user.username,
        password=user.password,
        email=user.email
    )


@router.post(
    "/login",
    response_model=UserResponse
)
def login_user(
    credentials: UserLogin,
    db: Session = Depends(get_db)
):

    user = authenticate_user(
        db,
        login=credentials.login,
        password=credentials.password
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid username/email or password"
        )

    return user


@router.get(
    "/{user_id}",
    response_model=UserResponse
)
def get_user(
    user_id: int,
    db: Session = Depends(get_db)
):

    user = get_user_by_id(db, user_id)

    return user
