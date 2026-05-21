from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.Database.connection import (
    engine,
    Base
)

import app.Database.models

from app.Routers.user_router import router as user_router
from app.Routers.habit_router import router as habit_router
from app.Routers.statistics_router import (
    router as statistics_router
)
from app.Routers.web_router import router as web_router

from app.Exceptions.exceptions import (
    UserAlreadyExistsException,
    UserNotFoundException,
    HabitNotFoundException,
    HabitAlreadyCompletedException
)

from app.Exceptions.handlers import (
    user_exists_handler,
    user_not_found_handler,
    habit_not_found_handler,
    habit_completed_handler
)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Habit Tracker API"
)

BASE_DIR = Path(__file__).resolve().parent

app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "app" / "static")),
    name="static"
)

app.include_router(user_router)
app.include_router(habit_router)
app.include_router(statistics_router)
app.include_router(web_router)

app.add_exception_handler(
    UserAlreadyExistsException,
    user_exists_handler
)

app.add_exception_handler(
    UserNotFoundException,
    user_not_found_handler
)

app.add_exception_handler(
    HabitNotFoundException,
    habit_not_found_handler
)

app.add_exception_handler(
    HabitAlreadyCompletedException,
    habit_completed_handler
)


@app.get("/", include_in_schema=False)
def root():

    return RedirectResponse(url="/app")


@app.get("/api/health")
def health():

    return {
        "message": "Habit Tracker API works"
    }
