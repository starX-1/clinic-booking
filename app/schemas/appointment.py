from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.appointment import AppointmentStatus
from app.schemas.doctor import DoctorResponse


class AppointmentCreate(BaseModel):
    doctor_id: int
    patient_id: int
    start_time: datetime = Field(
        ..., description="Appointment start time in ISO format (e.g. 2026-08-20T10:00:00Z)"
    )


class AppointmentCancelRequest(BaseModel):
    reason: str = Field(..., min_length=3, description="Reason for cancellation")


class AppointmentRescheduleRequest(BaseModel):
    new_start_time: datetime = Field(
        ..., description="New appointment start time in ISO format (e.g. 2026-08-20T11:00:00Z)"
    )


class DoctorSimpleResponse(BaseModel):
    id: int
    name: str
    specialization: str

    model_config = ConfigDict(from_attributes=True)


class PatientSimpleResponse(BaseModel):
    id: int
    name: str
    email: str

    model_config = ConfigDict(from_attributes=True)


class AppointmentResponse(BaseModel):
    id: int
    doctor_id: int
    patient_id: int
    start_time: datetime
    end_time: datetime
    status: AppointmentStatus
    cancellation_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    doctor: Optional[DoctorSimpleResponse] = None
    patient: Optional[PatientSimpleResponse] = None

    model_config = ConfigDict(from_attributes=True)
