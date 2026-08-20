from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.appointment import AppointmentResponse
from app.services.appointment_service import get_patient_upcoming_appointments

router = APIRouter(prefix="/patients", tags=["Patients"])


@router.get(
    "/{id}/appointments",
    response_model=List[AppointmentResponse],
    summary="Get patient upcoming appointments (Bonus)",
    description="Retrieve upcoming booked appointments for a patient sorted chronologically by date.",
)
async def get_patient_appointments(id: int, db: AsyncSession = Depends(get_db)):
    return await get_patient_upcoming_appointments(db, id)
