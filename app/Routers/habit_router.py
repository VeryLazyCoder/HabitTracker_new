from datetime import date

from fastapi import (
    APIRouter,
    Depends,
    Query
)

from sqlalchemy.orm import Session

from app.Database.connection import get_db

from app.Schemas.habit_schema import (
    HabitCreate,
    HabitUpdate,
    HabitResponse,
    HabitLogResponse
)

from app.Services.habit_service import (
    create_habit,
    get_user_habits,
    get_habit_by_id,
    update_habit,
    delete_habit,
    complete_habit,
    undo_habit_progress
)
from app.Utils.enums import HabitType

router = APIRouter(
    prefix="/habits",
    tags=["Habits"]
)


@router.post(
    "/{user_id}",
    response_model=HabitResponse
)
def create_new_habit(
    user_id: int,
    habit: HabitCreate,
    db: Session = Depends(get_db)
):

    created_habit = create_habit(
        db,
        user_id=user_id,
        title=habit.title,
        description=habit.description,
        habit_type=habit.type,
        target_count=habit.target_count
    )

    return created_habit


@router.get(
    "/{user_id}",
    response_model=list[HabitResponse]
)
def get_habits(
    user_id: int,
    search: str | None = None,
    habit_type: HabitType | None = None,
    sort_by: str = Query("created_at", pattern="^(title|type|created_at)$"),
    sort_dir: str = Query("desc", pattern="^(asc|desc)$"),
    completion_status: str = Query("all", pattern="^(all|completed|missed)$"),
    completion_date: date | None = None,
    db: Session = Depends(get_db)
):

    return get_user_habits(
        context=db,
        user_id=user_id,
        search=search,
        habit_type=habit_type,
        sort_by=sort_by,
        sort_dir=sort_dir,
        completion_status=completion_status,
        completion_date=completion_date
    )


@router.get(
    "/{user_id}/{habit_id}",
    response_model=HabitResponse
)
def get_habit(
    user_id: int,
    habit_id: int,
    db: Session = Depends(get_db)
):
    habit = get_habit_by_id(
        db,
        habit_id,
        user_id
    )

    return habit


@router.put(
    "/{user_id}/{habit_id}",
    response_model=HabitResponse
)
def update_existing_habit(
    user_id: int,
    habit_id: int,
    habit: HabitUpdate,
    db: Session = Depends(get_db)
):
    updated_habit = update_habit(
        db,
        habit_id=habit_id,
        user_id=user_id,
        title=habit.title,
        description=habit.description,
        habit_type=habit.type,
        target_count=habit.target_count
    )

    return updated_habit



@router.delete(
    "/{user_id}/{habit_id}"
)
def delete_existing_habit(
    user_id: int,
    habit_id: int,
    db: Session = Depends(get_db)
):
    delete_habit(
        db,
        habit_id,
        user_id
    )

    return {
        "message": "Habit deleted"
    }



@router.post(
    "/{user_id}/{habit_id}/complete",
    response_model=HabitLogResponse
)
def complete_existing_habit(
    user_id: int,
    habit_id: int,
    completed_date: date,
    amount: int = Query(1, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    log = complete_habit(
        db,
        habit_id=habit_id,
        user_id=user_id,
        completed_date=completed_date,
        amount=amount
    )

    return log


@router.post(
    "/{user_id}/{habit_id}/undo"
)
def undo_existing_habit_progress(
    user_id: int,
    habit_id: int,
    completed_date: date,
    db: Session = Depends(get_db)
):

    undo_habit_progress(
        db,
        habit_id=habit_id,
        user_id=user_id,
        completed_date=completed_date
    )

    return {
        "message": "Habit mark removed"
    }
