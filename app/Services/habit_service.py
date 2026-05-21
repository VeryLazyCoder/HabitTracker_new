from datetime import date

from sqlalchemy import asc, desc, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import app.Database.models as model
from app.Exceptions.exceptions import (
    HabitAlreadyCompletedException,
    HabitNotFoundException,
    UserNotFoundException
)
from app.Utils.enums import HabitType


def _target_for_type(habit_type: HabitType, target_count: int | None) -> int:
    if habit_type == HabitType.BAD:
        return 1

    return max(1, target_count or 1)


def _get_log_for_date(
    context: Session,
    habit_id: int,
    completed_date: date
):
    return (
        context.query(model.HabitLog)
        .filter(
            model.HabitLog.habit_id == habit_id,
            model.HabitLog.completed_date == completed_date
        )
        .first()
    )


def is_habit_successful(
    habit: model.Habit,
    log: model.HabitLog | None
) -> bool:
    if habit.type == HabitType.BAD:
        return log is None

    return bool(log and log.progress >= _target_for_type(habit.type, habit.target_count))


def build_habit_day_status(
    habit: model.Habit,
    log: model.HabitLog | None,
    status_date: date
) -> dict:
    target_count = _target_for_type(habit.type, habit.target_count)
    is_active = status_date >= habit.created_at.date()

    if not is_active:
        return {
            "date": status_date,
            "has_log": log is not None,
            "is_active": False,
            "is_complete": False,
            "progress": 0,
            "target_count": target_count,
            "progress_percent": 0,
            "progress_text": "не создана",
            "status_text": "Еще не создана",
            "action_text": "Отметить срыв" if habit.type == HabitType.BAD else "+1",
            "undo_text": "Убрать срыв" if habit.type == HabitType.BAD else "Убрать отметку",
            "is_bad": habit.type == HabitType.BAD
        }

    if habit.type == HabitType.BAD:
        has_relapse = log is not None
        return {
            "date": status_date,
            "has_log": has_relapse,
            "is_active": True,
            "is_complete": not has_relapse,
            "progress": 0 if has_relapse else 1,
            "target_count": 1,
            "progress_percent": 0 if has_relapse else 100,
            "progress_text": "срыв" if has_relapse else "без срыва",
            "status_text": "Срыв отмечен" if has_relapse else "Без срыва",
            "action_text": "Отметить срыв",
            "undo_text": "Убрать срыв",
            "is_bad": True
        }

    progress = log.progress if log else 0
    visible_progress = min(progress, target_count)
    is_complete = progress >= target_count

    return {
        "date": status_date,
        "has_log": log is not None,
        "is_active": True,
        "is_complete": is_complete,
        "progress": progress,
        "target_count": target_count,
        "progress_percent": round((visible_progress / target_count) * 100),
        "progress_text": f"{visible_progress}/{target_count}",
        "status_text": "Выполнено" if is_complete else "В процессе",
        "action_text": "+1",
        "undo_text": "Убрать отметку",
        "is_bad": False
    }


def create_habit(
    context: Session,
    user_id: int,
    title: str,
    habit_type,
    description: str | None = None,
    target_count: int = 1
):

    user_exists = (
        context.query(model.User.id)
        .filter(model.User.id == user_id)
        .first()
    )

    if not user_exists:
        raise UserNotFoundException(
            "User not found"
        )

    try:
        habit = model.Habit(
            title=title,
            description=description,
            type=habit_type,
            target_count=_target_for_type(habit_type, target_count),
            user_id=user_id
        )

        context.add(habit)
        context.commit()
        context.refresh(habit)

        return habit

    except Exception:
        context.rollback()
        raise


def get_user_habits(
    context: Session,
    user_id: int,
    search: str | None = None,
    habit_type=None,
    sort_by: str = "created_at",
    sort_dir: str = "desc",
    completion_status: str = "all",
    completion_date: date | None = None
):

    query = (
        context.query(model.Habit)
        .filter(model.Habit.user_id == user_id)
    )

    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                model.Habit.title.ilike(pattern),
                model.Habit.description.ilike(pattern)
            )
        )

    if habit_type:
        query = query.filter(model.Habit.type == habit_type)

    sort_columns = {
        "title": model.Habit.title,
        "type": model.Habit.type,
        "created_at": model.Habit.created_at
    }
    sort_column = sort_columns.get(sort_by, model.Habit.created_at)
    query = query.order_by(desc(sort_column) if sort_dir == "desc" else asc(sort_column))

    habits = query.all()

    if completion_date and completion_status in {"completed", "missed"}:
        statuses = get_habit_day_statuses(
            context,
            user_id,
            completion_date,
            habits=habits
        )
        habits = [
            habit
            for habit in habits
            if statuses[habit.id]["is_complete"] == (completion_status == "completed")
        ]

    return habits


def get_habit_by_id(
    context: Session,
    habit_id: int,
    user_id: int
):

    habit = (
        context.query(model.Habit)
        .filter(
            model.Habit.id == habit_id,
            model.Habit.user_id == user_id
        )
        .first()
    )

    if not habit:
        raise HabitNotFoundException(
            "Habit not found"
        )

    return habit


def get_habit_day_statuses(
    context: Session,
    user_id: int,
    status_date: date,
    habits: list[model.Habit] | None = None
) -> dict[int, dict]:

    if habits is None:
        habits = (
            context.query(model.Habit)
            .filter(model.Habit.user_id == user_id)
            .all()
        )

    habit_ids = [habit.id for habit in habits]

    if not habit_ids:
        return {}

    logs = (
        context.query(model.HabitLog)
        .join(model.Habit)
        .filter(
            model.Habit.user_id == user_id,
            model.HabitLog.habit_id.in_(habit_ids),
            model.HabitLog.completed_date == status_date
        )
        .all()
    )
    logs_by_habit = {
        log.habit_id: log
        for log in logs
    }

    return {
        habit.id: build_habit_day_status(
            habit,
            logs_by_habit.get(habit.id),
            status_date
        )
        for habit in habits
    }


def get_habit_logs(
    context: Session,
    habit_id: int,
    user_id: int,
    start_date: date | None = None,
    end_date: date | None = None
):

    get_habit_by_id(
        context,
        habit_id,
        user_id
    )

    query = (
        context.query(model.HabitLog)
        .filter(model.HabitLog.habit_id == habit_id)
    )

    if start_date:
        query = query.filter(model.HabitLog.completed_date >= start_date)

    if end_date:
        query = query.filter(model.HabitLog.completed_date <= end_date)

    return (
        query
        .order_by(model.HabitLog.completed_date.desc())
        .all()
    )


def update_habit(
    context: Session,
    habit_id: int,
    user_id: int,
    title: str | None = None,
    description: str | None = None,
    habit_type=None,
    target_count: int | None = None
):

    habit = get_habit_by_id(
        context,
        habit_id,
        user_id
    )

    try:
        if title is not None:
            habit.title = title

        if description is not None:
            habit.description = description

        if habit_type is not None:
            habit.type = habit_type

        habit.target_count = _target_for_type(
            habit.type,
            target_count if target_count is not None else habit.target_count
        )

        context.commit()
        context.refresh(habit)

        return habit

    except Exception:
        context.rollback()
        raise


def delete_habit(
    context: Session,
    habit_id: int,
    user_id: int
):

    habit = get_habit_by_id(
        context,
        habit_id,
        user_id
    )

    try:
        context.delete(habit)
        context.commit()

    except Exception:
        context.rollback()
        raise


def complete_habit(
    context: Session,
    habit_id: int,
    user_id: int,
    completed_date: date,
    amount: int = 1
):

    habit = get_habit_by_id(
        context,
        habit_id,
        user_id
    )
    target_count = _target_for_type(habit.type, habit.target_count)
    amount = max(1, amount)
    existing_log = _get_log_for_date(context, habit_id, completed_date)

    if habit.type == HabitType.BAD and existing_log:
        raise HabitAlreadyCompletedException(
            "Relapse already marked for this date"
        )

    if habit.type != HabitType.BAD and existing_log:
        if existing_log.progress >= target_count:
            raise HabitAlreadyCompletedException(
                "Habit already completed for this date"
            )

        try:
            existing_log.progress = min(target_count, existing_log.progress + amount)
            context.commit()
            context.refresh(existing_log)
            return existing_log

        except Exception:
            context.rollback()
            raise

    try:
        log = model.HabitLog(
            habit_id=habit_id,
            completed_date=completed_date,
            progress=min(target_count, amount)
        )

        context.add(log)
        context.commit()
        context.refresh(log)

        return log

    except IntegrityError:
        context.rollback()

        raise HabitAlreadyCompletedException(
            "Habit already marked for this date"
        )

    except Exception:
        context.rollback()
        raise


def undo_habit_progress(
    context: Session,
    habit_id: int,
    user_id: int,
    completed_date: date
):

    habit = get_habit_by_id(
        context,
        habit_id,
        user_id
    )
    existing_log = _get_log_for_date(context, habit_id, completed_date)

    if not existing_log:
        return None

    try:
        if habit.type != HabitType.BAD and existing_log.progress > 1:
            existing_log.progress -= 1
            context.commit()
            context.refresh(existing_log)
            return existing_log

        context.delete(existing_log)
        context.commit()
        return None

    except Exception:
        context.rollback()
        raise
