from datetime import date, timedelta
from pathlib import Path
from urllib.parse import parse_qs, parse_qsl, quote, urlencode, urlsplit, urlunsplit

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.Auth.security import (
    clear_session_cookie,
    get_session_user_id,
    set_session_cookie
)
from app.Database.connection import get_db
from app.Exceptions.exceptions import (
    HabitAlreadyCompletedException,
    HabitNotFoundException,
    UserAlreadyExistsException,
    UserNotFoundException
)
from app.Schemas.user_schema import validate_email
from app.Services.habit_service import (
    complete_habit,
    create_habit,
    delete_habit,
    get_habit_day_statuses,
    get_habit_by_id,
    get_habit_logs,
    get_user_habits,
    update_habit,
    undo_habit_progress
)
from app.Services.statistics_service import (
    get_habit_statistics,
    get_user_statistics
)
from app.Services.user_service import (
    authenticate_user,
    create_user,
    get_user_by_id
)
from app.Utils.enums import HabitType

BASE_DIR = Path(__file__).resolve().parents[1]
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter(
    prefix="/app",
    tags=["Web"]
)


def _redirect(url: str) -> RedirectResponse:
    return RedirectResponse(url=url, status_code=303)


async def _parse_form(request: Request) -> dict[str, str]:
    body = (await request.body()).decode("utf-8")
    parsed = parse_qs(body, keep_blank_values=True)
    return {
        key: values[-1].strip()
        for key, values in parsed.items()
    }


def _current_path(request: Request) -> str:
    path = request.url.path
    if request.url.query:
        path = f"{path}?{request.url.query}"
    return path


def _login_redirect(request: Request) -> RedirectResponse:
    return _redirect(f"/app/login?next={quote(_current_path(request))}")


def _safe_next(value: str | None) -> str:
    if value and value.startswith("/app") and "//" not in value:
        return _strip_flash_params(value)
    return "/app/habits"


def _strip_flash_params(url: str) -> str:
    parts = urlsplit(url)
    clean_query = urlencode(
        [
            (key, value)
            for key, value in parse_qsl(parts.query, keep_blank_values=True)
            if key not in {"message", "error"}
        ]
    )
    return urlunsplit(("", "", parts.path, clean_query, parts.fragment))


def _current_user(request: Request, db: Session):
    user_id = get_session_user_id(request)

    if not user_id:
        return None

    try:
        return get_user_by_id(db, user_id)
    except UserNotFoundException:
        return None


def _parse_date(value: str | None, default: date) -> date:
    if not value:
        return default

    try:
        return date.fromisoformat(value)
    except ValueError:
        return default


def _parse_interval(request: Request) -> tuple[date, date, str]:
    today = date.today()
    period = request.query_params.get("period", "week")

    if period == "month":
        default_start = today - timedelta(days=29)
    else:
        period = "week"
        default_start = today - timedelta(days=6)

    start_date = _parse_date(request.query_params.get("start_date"), default_start)
    end_date = _parse_date(request.query_params.get("end_date"), today)

    if end_date < start_date:
        start_date, end_date = end_date, start_date

    return start_date, end_date, period


def _build_query(**params) -> str:
    clean_params = {
        key: value
        for key, value in params.items()
        if value not in (None, "")
    }
    return urlencode(clean_params)


def _template_context(request: Request, user=None, **extra):
    context = {
        "request": request,
        "current_user": user,
        "habit_types": HabitType,
        "message": request.query_params.get("message"),
        "error": request.query_params.get("error")
    }
    context.update(extra)
    return context


def _habit_form_values(form: dict[str, str]) -> tuple[
    str,
    str | None,
    HabitType | None,
    int,
    str | None
]:
    title = form.get("title", "")
    description = form.get("description") or None
    habit_type_value = form.get("type", HabitType.GOOD.value)
    target_count_value = form.get("target_count", "1")

    try:
        habit_type = HabitType(habit_type_value)
    except ValueError:
        habit_type = None

    try:
        target_count = int(target_count_value)
    except ValueError:
        target_count = 0

    if habit_type == HabitType.BAD:
        target_count = 1

    if len(title) < 2:
        return title, description, habit_type, target_count, "Название должно быть не короче 2 символов."

    if description and len(description) > 500:
        return title, description, habit_type, target_count, "Описание должно быть не длиннее 500 символов."

    if not habit_type:
        return title, description, habit_type, target_count, "Выберите корректный тип привычки."

    if target_count < 1 or target_count > 1000:
        return title, description, habit_type, target_count, "Цель за день должна быть от 1 до 1000."

    return title, description, habit_type, target_count, None


@router.get("", response_class=HTMLResponse)
def index(
    request: Request,
    db: Session = Depends(get_db)
):
    user = _current_user(request, db)

    if user:
        return _redirect("/app/habits")

    return _redirect("/app/login")


@router.get("/login", response_class=HTMLResponse)
def login_page(
    request: Request,
    db: Session = Depends(get_db)
):
    user = _current_user(request, db)

    if user:
        return _redirect("/app/habits")

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context=_template_context(
            request,
            next_url=_safe_next(request.query_params.get("next")),
            form={}
        )
    )


@router.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    db: Session = Depends(get_db)
):
    form = await _parse_form(request)
    user = authenticate_user(
        db,
        login=form.get("login", ""),
        password=form.get("password", "")
    )

    if not user:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context=_template_context(
                request,
                form=form,
                next_url=_safe_next(form.get("next")),
                error="Неверный логин, email или пароль."
            ),
            status_code=400
        )

    response = _redirect(_safe_next(form.get("next")))
    set_session_cookie(response, user.id)
    return response


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="register.html",
        context=_template_context(request, form={})
    )


@router.post("/register", response_class=HTMLResponse)
async def register_submit(
    request: Request,
    db: Session = Depends(get_db)
):
    form = await _parse_form(request)
    username = form.get("username", "")
    email = form.get("email", "")
    password = form.get("password", "")

    error = None
    if len(username) < 3:
        error = "Имя пользователя должно быть не короче 3 символов."
    elif len(password) < 6:
        error = "Пароль должен быть не короче 6 символов."
    else:
        try:
            email = validate_email(email)
        except ValueError:
            error = "Укажите корректный email."

    if error:
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context=_template_context(request, form=form, error=error),
            status_code=400
        )

    try:
        user = create_user(
            db,
            username=username,
            email=email,
            password=password
        )
    except UserAlreadyExistsException:
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context=_template_context(
                request,
                form=form,
                error="Пользователь с таким именем или email уже существует."
            ),
            status_code=400
        )

    response = _redirect("/app/habits?message=Аккаунт создан.")
    set_session_cookie(response, user.id)
    return response


@router.post("/logout")
def logout():
    response = _redirect("/app/login?message=Вы вышли из аккаунта.")
    clear_session_cookie(response)
    return response


@router.get("/habits", response_class=HTMLResponse)
def habits_page(
    request: Request,
    db: Session = Depends(get_db)
):
    user = _current_user(request, db)

    if not user:
        return _login_redirect(request)

    start_date, end_date, period = _parse_interval(request)
    selected_date = _parse_date(request.query_params.get("completion_date"), date.today())
    type_value = request.query_params.get("type")
    habit_type = HabitType(type_value) if type_value in {item.value for item in HabitType} else None
    sort_by = request.query_params.get("sort_by", "created_at")
    sort_dir = request.query_params.get("sort_dir", "desc")
    completion_status = request.query_params.get("completion_status", "all")

    if sort_by not in {"title", "type", "created_at"}:
        sort_by = "created_at"
    if sort_dir not in {"asc", "desc"}:
        sort_dir = "desc"
    if completion_status not in {"all", "completed", "missed"}:
        completion_status = "all"

    habits = get_user_habits(
        context=db,
        user_id=user.id,
        search=request.query_params.get("search"),
        habit_type=habit_type,
        sort_by=sort_by,
        sort_dir=sort_dir,
        completion_status=completion_status,
        completion_date=selected_date
    )
    daily_statuses = get_habit_day_statuses(db, user.id, selected_date, habits=habits)
    stats = get_user_statistics(db, user.id, start_date, end_date)

    return templates.TemplateResponse(
        request=request,
        name="habits.html",
        context=_template_context(
            request,
            user=user,
            habits=habits,
            daily_statuses=daily_statuses,
            selected_date=selected_date,
            stats=stats,
            period=period,
            start_date=start_date,
            end_date=end_date,
            filters={
                "search": request.query_params.get("search", ""),
                "type": type_value or "",
                "sort_by": sort_by,
                "sort_dir": sort_dir,
                "completion_status": completion_status
            }
        )
    )


@router.get("/habits/new", response_class=HTMLResponse)
def new_habit_page(
    request: Request,
    db: Session = Depends(get_db)
):
    user = _current_user(request, db)

    if not user:
        return _login_redirect(request)

    return templates.TemplateResponse(
        request=request,
        name="habit_form.html",
        context=_template_context(
            request,
            user=user,
            mode="create",
            form={
                "title": "",
                "description": "",
                "type": HabitType.GOOD.value,
                "target_count": 1
            },
            habit=None
        )
    )


@router.post("/habits", response_class=HTMLResponse)
async def create_habit_submit(
    request: Request,
    db: Session = Depends(get_db)
):
    user = _current_user(request, db)

    if not user:
        return _login_redirect(request)

    form = await _parse_form(request)
    title, description, habit_type, target_count, error = _habit_form_values(form)

    if error:
        return templates.TemplateResponse(
            request=request,
            name="habit_form.html",
            context=_template_context(
                request,
                user=user,
                mode="create",
                form=form,
                habit=None,
                error=error
            ),
            status_code=400
        )

    create_habit(
        db,
        user_id=user.id,
        title=title,
        description=description,
        habit_type=habit_type,
        target_count=target_count
    )

    return _redirect("/app/habits?message=Привычка создана.")


@router.get("/habits/{habit_id}", response_class=HTMLResponse)
def habit_detail_page(
    habit_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    user = _current_user(request, db)

    if not user:
        return _login_redirect(request)

    start_date, end_date, period = _parse_interval(request)

    try:
        habit = get_habit_by_id(db, habit_id, user.id)
        stats = get_habit_statistics(db, habit_id, start_date, end_date, user_id=user.id)
        logs = get_habit_logs(db, habit_id, user.id, start_date, end_date)
        selected_date = _parse_date(request.query_params.get("completion_date"), date.today())
        daily_status = get_habit_day_statuses(
            db,
            user.id,
            selected_date,
            habits=[habit]
        )[habit.id]
    except HabitNotFoundException:
        return _redirect("/app/habits?error=Привычка не найдена.")

    return templates.TemplateResponse(
        request=request,
        name="habit_detail.html",
        context=_template_context(
            request,
            user=user,
            habit=habit,
            stats=stats,
            logs=logs,
            daily_status=daily_status,
            period=period,
            start_date=start_date,
            end_date=end_date,
            selected_date=selected_date
        )
    )


@router.get("/habits/{habit_id}/edit", response_class=HTMLResponse)
def edit_habit_page(
    habit_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    user = _current_user(request, db)

    if not user:
        return _login_redirect(request)

    try:
        habit = get_habit_by_id(db, habit_id, user.id)
    except HabitNotFoundException:
        return _redirect("/app/habits?error=Привычка не найдена.")

    return templates.TemplateResponse(
        request=request,
        name="habit_form.html",
        context=_template_context(
            request,
            user=user,
            mode="edit",
            habit=habit,
            form={
                "title": habit.title,
                "description": habit.description or "",
                "type": habit.type.value,
                "target_count": habit.target_count
            }
        )
    )


@router.post("/habits/{habit_id}/edit", response_class=HTMLResponse)
async def edit_habit_submit(
    habit_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    user = _current_user(request, db)

    if not user:
        return _login_redirect(request)

    form = await _parse_form(request)
    title, description, habit_type, target_count, error = _habit_form_values(form)

    try:
        habit = get_habit_by_id(db, habit_id, user.id)
    except HabitNotFoundException:
        return _redirect("/app/habits?error=Привычка не найдена.")

    if error:
        return templates.TemplateResponse(
            request=request,
            name="habit_form.html",
            context=_template_context(
                request,
                user=user,
                mode="edit",
                habit=habit,
                form=form,
                error=error
            ),
            status_code=400
        )

    update_habit(
        db,
        habit_id=habit_id,
        user_id=user.id,
        title=title,
        description=description,
        habit_type=habit_type,
        target_count=target_count
    )

    return _redirect(f"/app/habits/{habit_id}?message=Привычка обновлена.")


@router.post("/habits/{habit_id}/delete")
def delete_habit_submit(
    habit_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    user = _current_user(request, db)

    if not user:
        return _login_redirect(request)

    try:
        delete_habit(db, habit_id, user.id)
    except HabitNotFoundException:
        return _redirect("/app/habits?error=Привычка не найдена.")

    return _redirect("/app/habits?message=Привычка удалена.")


@router.post("/habits/{habit_id}/complete")
async def complete_habit_submit(
    habit_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    user = _current_user(request, db)

    if not user:
        return _login_redirect(request)

    form = await _parse_form(request)
    completed_date = _parse_date(form.get("completed_date"), date.today())
    return_to = _safe_next(form.get("return_to"))
    amount = 1

    try:
        amount = max(1, int(form.get("amount", "1")))
    except ValueError:
        amount = 1

    try:
        complete_habit(
            db,
            habit_id=habit_id,
            user_id=user.id,
            completed_date=completed_date,
            amount=amount
        )
    except HabitAlreadyCompletedException:
        glue = "&" if "?" in return_to else "?"
        return _redirect(f"{return_to}{glue}{_build_query(error='Эта дата уже полностью отмечена.')}")
    except HabitNotFoundException:
        return _redirect("/app/habits?error=Привычка не найдена.")

    glue = "&" if "?" in return_to else "?"
    return _redirect(f"{return_to}{glue}{_build_query(message='Отметка сохранена.')}")


@router.post("/habits/{habit_id}/undo")
async def undo_habit_submit(
    habit_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    user = _current_user(request, db)

    if not user:
        return _login_redirect(request)

    form = await _parse_form(request)
    completed_date = _parse_date(form.get("completed_date"), date.today())
    return_to = _safe_next(form.get("return_to"))

    try:
        undo_habit_progress(
            db,
            habit_id=habit_id,
            user_id=user.id,
            completed_date=completed_date
        )
    except HabitNotFoundException:
        return _redirect("/app/habits?error=Привычка не найдена.")

    glue = "&" if "?" in return_to else "?"
    return _redirect(f"{return_to}{glue}{_build_query(message='Отметка убрана.')}")
