from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base

class Gear(Base):
    __tablename__ = "gear_items"

    id: Mapped[int] = mapped_column(
            primary_key=True,
            autoincrement=True,
        )

    description: Mapped[str] = mapped_column(
        String(100),
        nullable=True
    )

#Owned, borrowed, missing
    status: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
    )

    return_date: Mapped[str] = mapped_column(
        String(10),
        nullable=True,
    )




class Gear_List(Base):
    __tablename__ = "gear_list"



