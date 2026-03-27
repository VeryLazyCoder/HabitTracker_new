from sqlalchemy.orm import Session
from Database.connection import get_db
import Database.models as model
import datetime

def create_user(context: Session, username: str, password: str, email: str) -> model.User:
    user = model.User(
        username=username,
        password=password,
        email=email
    )
    context.add(user)
    context.commit()
    context.refresh(user)
    return user

create_user(get_db(), "First", "123", "ya@.gmail.com")