from pydantic import (
    BaseModel,
    Field
)

from datetime import (
    date,
    datetime
)

from typing import Optional

from app.Utils.enums import HabitType


class HabitCreate(BaseModel):

    title: str = Field(
        min_length=2,
        max_length=100
    )

    description: Optional[str] = Field(
        default=None,
        max_length=500
    )

    type: HabitType

    target_count: int = Field(
        default=1,
        ge=1,
        le=1000
    )


class HabitUpdate(BaseModel):

    title: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=100
    )

    description: Optional[str] = Field(
        default=None,
        max_length=500
    )

    type: Optional[HabitType] = None

    target_count: Optional[int] = Field(
        default=None,
        ge=1,
        le=1000
    )


class HabitResponse(BaseModel):

    id: int

    title: str

    description: Optional[str]

    type: HabitType

    target_count: int

    created_at: datetime

    class Config:
        from_attributes = True


class HabitLogResponse(BaseModel):

    id: int

    completed_date: date

    progress: int

    class Config:
        from_attributes = True
