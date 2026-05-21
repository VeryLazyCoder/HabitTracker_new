from pydantic import (
    BaseModel,
    Field,
    field_validator
)

from datetime import datetime


def validate_email(value: str) -> str:
    value = value.strip().lower()
    if "@" not in value or "." not in value.rsplit("@", 1)[-1]:
        raise ValueError("Invalid email address")
    return value


class UserCreate(BaseModel):

    username: str = Field(
        min_length=3,
        max_length=30
    )

    email: str

    password: str = Field(
        min_length=6,
        max_length=100
    )

    @field_validator("email")
    @classmethod
    def email_must_be_valid(cls, value: str) -> str:
        return validate_email(value)


class UserLogin(BaseModel):

    login: str = Field(
        min_length=3,
        max_length=100
    )

    password: str = Field(
        min_length=6,
        max_length=100
    )


class UserResponse(BaseModel):

    id: int

    username: str

    email: str

    created_at: datetime

    class Config:
        from_attributes = True
