from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    location: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    start_date: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    end_date: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )


#Continue here: wish-to-go




