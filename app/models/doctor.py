from datetime import time
from typing import List, TYPE_CHECKING
from sqlalchemy import ForeignKey, Integer, String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.appointment import Appointment


class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    specialization: Mapped[str] = mapped_column(String(100), nullable=False, default="General Practitioner")

    working_hours: Mapped[List["DoctorWorkingHours"]] = relationship(
        "DoctorWorkingHours", back_populates="doctor", cascade="all, delete-orphan", lazy="selectin"
    )
    appointments: Mapped[List["Appointment"]] = relationship(
        "Appointment", back_populates="doctor", cascade="all, delete-orphan"
    )


class DoctorWorkingHours(Base):
    __tablename__ = "doctor_working_hours"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)  # 0 = Monday, 6 = Sunday
    start_time: Mapped[time] = mapped_column(Time, nullable=False)    # e.g., 09:00:00
    end_time: Mapped[time] = mapped_column(Time, nullable=False)      # e.g., 17:00:00

    doctor: Mapped["Doctor"] = relationship("Doctor", back_populates="working_hours")
