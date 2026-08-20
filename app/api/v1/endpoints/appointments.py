from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentCancelRequest,
    AppointmentRescheduleRequest,
    AppointmentResponse,
)
from app.services.appointment_service import (
    create_appointment,
    cancel_appointment,
    reschedule_appointment,
)

router = APIRouter(prefix="/appointments", tags=["Appointments"])


@router.post(
    "",
    response_model=AppointmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Book a slot",
    description="Book a 30-minute appointment slot for a doctor. Validates doctor working hours, lead time (>=1 hour in advance), and slot availability.",
)
async def book_appointment(payload: AppointmentCreate, db: AsyncSession = Depends(get_db)):
    return await create_appointment(db, payload)


@router.patch(
    "/{id}/cancel",
    response_model=AppointmentResponse,
    summary="Cancel an appointment",
    description="Cancel an appointment with a reason. Frees the 30-minute slot for other patients. Returns an error if already cancelled.",
)
async def cancel_appt(
    id: int, payload: AppointmentCancelRequest, db: AsyncSession = Depends(get_db)
):
    return await cancel_appointment(db, id, payload)


@router.patch(
    "/{id}/reschedule",
    response_model=AppointmentResponse,
    summary="Reschedule an appointment",
    description="Move an existing appointment to a new 30-minute slot. Validates the new slot and frees the old slot atomically.",
)
async def reschedule_appt(
    id: int, payload: AppointmentRescheduleRequest, db: AsyncSession = Depends(get_db)
):
    return await reschedule_appointment(db, id, payload)
