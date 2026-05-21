from datetime import date

from fastapi import (
    APIRouter,
    Depends,
    Query
)

from sqlalchemy.orm import Session

from app.Database.connection import get_db

from app.Services.statistics_service import (
    get_habit_statistics,
    get_user_statistics
)

router = APIRouter(
    prefix="/statistics",
    tags=["Statistics"]
)


@router.get(
    "/habit/{habit_id}"
)
def get_habit_stats(
    habit_id: int,
    start_date: date,
    end_date: date,
    user_id: int | None = Query(default=None),
    db: Session = Depends(get_db)
):

    return get_habit_statistics(
        context=db,
        habit_id=habit_id,
        start_date=start_date,
        end_date=end_date,
        user_id=user_id
    )


@router.get(
    "/user/{user_id}/habit/{habit_id}"
)
def get_user_habit_stats(
    user_id: int,
    habit_id: int,
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db)
):

    return get_habit_statistics(
        context=db,
        habit_id=habit_id,
        start_date=start_date,
        end_date=end_date,
        user_id=user_id
    )


@router.get(
    "/user/{user_id}"
)
def get_user_stats(
    user_id: int,
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db)
):

    return get_user_statistics(
        db,
        user_id,
        start_date,
        end_date
    )
