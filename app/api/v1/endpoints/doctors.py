from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.doctor import DoctorAvailabilityResponse
from app.services.availability_service import get_doctor_availability

router = APIRouter(prefix="/doctors", tags=["Doctors"])


@router.get(
    "/{id}/availability",
    response_model=DoctorAvailabilityResponse,
    summary="Get doctor availability",
    description="Return all available unbooked 30-minute slots for a doctor on a given date.",
)
async def get_availability(
    id: int,
    date: date = Query(..., description="Target date in YYYY-MM-DD format"),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await get_doctor_availability(db, id, date)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
