from datetime import date, time
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr


class DoctorWorkingHoursBase(BaseModel):
    day_of_week: int  # 0 = Monday, 6 = Sunday
    start_time: time
    end_time: time

    model_config = ConfigDict(from_attributes=True)


class DoctorBase(BaseModel):
    name: str
    email: EmailStr
    specialization: str = "General Practitioner"


class DoctorResponse(DoctorBase):
    id: int
    working_hours: List[DoctorWorkingHoursBase] = []

    model_config = ConfigDict(from_attributes=True)


class TimeSlot(BaseModel):
    start_time: str  # ISO string or HH:MM format e.g. "2026-08-20T09:00:00"
    end_time: str    # ISO string or HH:MM format e.g. "2026-08-20T09:30:00"
    is_available: bool = True


class DoctorAvailabilityResponse(BaseModel):
    doctor_id: int
    doctor_name: str
    date: date
    available_slots: List[TimeSlot]
