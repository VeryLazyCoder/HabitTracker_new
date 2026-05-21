from datetime import date, timedelta

from sqlalchemy.orm import Session

import app.Database.models as model
from app.Exceptions.exceptions import (
    HabitNotFoundException,
    UserNotFoundException
)
from app.Services.habit_service import is_habit_successful


def _days_count(start_date: date, end_date: date) -> int:
    if end_date < start_date:
        return 0

    return (end_date - start_date).days + 1


def _date_range(start_date: date, end_date: date) -> list[date]:
    total_days = _days_count(start_date, end_date)

    return [
        start_date + timedelta(days=offset)
        for offset in range(total_days)
    ]


def _habit_active_dates(
    habit: model.Habit,
    start_date: date,
    end_date: date
) -> list[date]:
    active_start = max(start_date, habit.created_at.date())

    if end_date < active_start:
        return []

    return _date_range(active_start, end_date)


def _logs_by_habit_and_date(logs: list[model.HabitLog]) -> dict[tuple[int, date], model.HabitLog]:
    return {
        (log.habit_id, log.completed_date): log
        for log in logs
    }


def get_habit_statistics(
    context: Session,
    habit_id: int,
    start_date: date,
    end_date: date,
    user_id: int | None = None
):

    habit_query = (
        context.query(model.Habit)
        .filter(model.Habit.id == habit_id)
    )

    if user_id is not None:
        habit_query = habit_query.filter(model.Habit.user_id == user_id)

    habit = habit_query.first()

    if not habit:
        raise HabitNotFoundException(
            "Habit not found"
        )

    logs = (
        context.query(model.HabitLog)
        .filter(
            model.HabitLog.habit_id == habit_id,
            model.HabitLog.completed_date >= start_date,
            model.HabitLog.completed_date <= end_date
        )
        .order_by(model.HabitLog.completed_date)
        .all()
    )

    logs_by_date = {
        log.completed_date: log
        for log in logs
    }
    active_dates = _habit_active_dates(habit, start_date, end_date)
    successful_dates = [
        current_date
        for current_date in active_dates
        if is_habit_successful(habit, logs_by_date.get(current_date))
    ]
    total_days = len(active_dates)
    completed_days = len(successful_dates)
    completion_rate = 0

    if total_days > 0:
        completion_rate = round(
            (completed_days / total_days) * 100,
            2
        )

    return {
        "habit_id": habit_id,
        "habit_title": habit.title,
        "completed_days": completed_days,
        "failed_days": total_days - completed_days,
        "total_days": total_days,
        "completion_rate": completion_rate,
        "completed_dates": successful_dates,
        "logged_dates": [log.completed_date for log in logs],
        "start_date": start_date,
        "end_date": end_date
    }


def get_user_statistics(
    context: Session,
    user_id: int,
    start_date: date,
    end_date: date
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

    habits = (
        context.query(model.Habit)
        .filter(model.Habit.user_id == user_id)
        .order_by(model.Habit.title)
        .all()
    )

    logs = (
        context.query(model.HabitLog)
        .join(model.Habit)
        .filter(
            model.Habit.user_id == user_id,
            model.HabitLog.completed_date >= start_date,
            model.HabitLog.completed_date <= end_date
        )
        .all()
    )
    logs_by_key = _logs_by_habit_and_date(logs)
    days_by_habit = {
        habit.id: _habit_active_dates(habit, start_date, end_date)
        for habit in habits
    }
    total_days = _days_count(start_date, end_date)
    habits_count = len(habits)
    total_possible = sum(len(days) for days in days_by_habit.values())
    completed_by_habit = {}

    for habit in habits:
        completed_by_habit[habit.id] = sum(
            1
            for current_date in days_by_habit[habit.id]
            if is_habit_successful(
                habit,
                logs_by_key.get((habit.id, current_date))
            )
        )

    completed_logs = sum(completed_by_habit.values())
    completion_rate = 0

    if total_possible > 0:
        completion_rate = round(
            (completed_logs / total_possible) * 100,
            2
        )

    return {
        "user_id": user_id,
        "habits_count": habits_count,
        "completed_logs": completed_logs,
        "total_days": total_days,
        "total_possible": total_possible,
        "completion_rate": completion_rate,
        "by_habit": [
            {
                "habit_id": habit.id,
                "title": habit.title,
                "completed_days": completed_by_habit.get(habit.id, 0),
                "completion_rate": round(
                    (completed_by_habit.get(habit.id, 0) / len(days_by_habit[habit.id])) * 100,
                    2
                ) if days_by_habit[habit.id] else 0
            }
            for habit in habits
        ],
        "start_date": start_date,
        "end_date": end_date
    }
