from fastapi import Request
from fastapi.responses import JSONResponse

from app.Exceptions.exceptions import (
    UserAlreadyExistsException,
    UserNotFoundException,
    HabitNotFoundException,
    HabitAlreadyCompletedException
)


async def user_exists_handler(
    request: Request,
    exc: Exception
):

    return JSONResponse(
        status_code=400,
        content={
            "detail": str(exc)
        }
    )


async def user_not_found_handler(
    request: Request,
    exc: Exception
):

    return JSONResponse(
        status_code=404,
        content={
            "detail": str(exc)
        }
    )


async def habit_not_found_handler(
    request: Request,
    exc: Exception
):

    return JSONResponse(
        status_code=404,
        content={
            "detail": str(exc)
        }
    )


async def habit_completed_handler(
    request: Request,
    exc: Exception
):

    return JSONResponse(
        status_code=400,
        content={
            "detail": str(exc)
        }
    )
