from sqlalchemy import (
    Integer,
    String,
    Text,
    ForeignKey,
    DateTime,
    Date,
    UniqueConstraint,
    Enum
)

from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import date, datetime
from app.Database.connection import Base
from app.Utils.enums import HabitType


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    username: Mapped[str] = mapped_column(
        String,
        unique=True,
        index=True,
        nullable=False
    )

    email: Mapped[str] = mapped_column(
        String,
        unique=True,
        index=True,
        nullable=False
    )

    password: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now
    )

    habits: Mapped[list["Habit"]] = relationship(
        "Habit",
        back_populates="owner",
        cascade="all, delete"
    )


class Habit(Base):
    __tablename__ = "habits"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    title: Mapped[str] = mapped_column(String, nullable=False)
    
    description: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now
    )

    type: Mapped[HabitType] = mapped_column(
        Enum(HabitType),
        nullable=False
    )

    target_count: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    owner: Mapped["User"] = relationship("User", back_populates="habits")
    logs: Mapped[list["HabitLog"]] = relationship(
        "HabitLog",
        back_populates="habit",
        cascade="all, delete"
    )


class HabitLog(Base):
    __tablename__ = "habit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    completed_date: Mapped[date] = mapped_column(
        Date,
        nullable=False
    )

    progress: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False
    )

    habit_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("habits.id", ondelete="CASCADE"),
        nullable=False
    )

    habit: Mapped["Habit"] = relationship(
        "Habit",
        back_populates="logs"
    )

    __table_args__ = (
        UniqueConstraint(
            "habit_id",
            "completed_date",
            name="uq_habit_date"
        ),
    )
