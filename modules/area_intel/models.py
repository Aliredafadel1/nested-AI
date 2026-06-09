from sqlalchemy import Integer, Numeric, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class Neighborhood(Base):
    __tablename__ = "neighborhoods"

    id:             Mapped[int]         = mapped_column(Integer, primary_key=True)
    name:           Mapped[str]         = mapped_column(String(100), unique=True, nullable=False)
    name_ar:        Mapped[str | None]  = mapped_column(String(100))
    city:           Mapped[str]         = mapped_column(String(100), default="Beirut")
    electricity:    Mapped[float | None]= mapped_column(Numeric(3, 1))
    generator_cost: Mapped[int | None]  = mapped_column(Integer)
    internet:       Mapped[int | None]  = mapped_column(SmallInteger)
    transport:      Mapped[int | None]  = mapped_column(SmallInteger)
    safety:         Mapped[int | None]  = mapped_column(SmallInteger)
    student_vibe:   Mapped[int | None]  = mapped_column(SmallInteger)
    lat:            Mapped[float | None]= mapped_column(Numeric(10, 7))
    lng:            Mapped[float | None]= mapped_column(Numeric(10, 7))
