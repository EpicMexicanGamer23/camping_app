import datetime

from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Gear(Base):
    """Individual gear item — the primary entity exposed via /gear endpoints."""

    __tablename__ = "gear_items"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    name: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        String(100),
        nullable=True,
    )

    # Allowed values: "owned" | "borrowed" | "missing"
    status: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    # Relevant when status == "borrowed" — the date the gear must be returned
    return_date: Mapped[datetime.date] = mapped_column(
        Date,
        nullable=True,
    )

    # Back-reference to any gear-list entries that include this item
    gear_list_entries: Mapped[list["Gear_List"]] = relationship(
        "Gear_List",
        back_populates="gear",
        cascade="all, delete-orphan",
    )


class Gear_List(Base):
    """
    Association table linking gear items to trips (many gear_items → one trip).
    Stored separately so a trip can have an arbitrary number of gear items.
    """

    __tablename__ = "gear_list"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    # Foreign key to gear_items — one row per gear item on the list
    gear_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("gear_items.id"),
        nullable=False,
    )

    # Trip ID (no FK because trips live in a separate service/database)
    trip_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    gear: Mapped["Gear"] = relationship("Gear", back_populates="gear_list_entries")



