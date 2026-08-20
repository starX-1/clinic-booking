from datetime import datetime, timedelta, time, timezone
from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.core.config import settings
from app.models.doctor import Doctor, DoctorWorkingHours
from app.models.patient import Patient
from app.models.appointment import Appointment, AppointmentStatus
from app.schemas.appointment import AppointmentCreate, AppointmentCancelRequest, AppointmentRescheduleRequest


def get_utc_now() -> datetime:
    """Returns naive datetime in UTC for clean database storage and comparison."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def normalize_datetime(dt: datetime) -> datetime:
    """Normalize input datetime to naive UTC datetime."""
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


async def validate_slot(
    db: AsyncSession, doctor_id: int, start_time: datetime, ignore_appointment_id: Optional[int] = None
) -> datetime:
    """
    Validates that a slot:
    1. Is aligned to 30-minute intervals (:00 or :30).
    2. Is in the future (not in the past).
    3. Respects minimum advance booking lead time (>= 1 hour from now).
    4. Falls within the doctor's working hours.
    5. Is not already booked by another active appointment.
    """
    start_time_clean = normalize_datetime(start_time)
    now = get_utc_now()

    # 1. 30-minute boundary check
    if start_time_clean.minute not in (0, 30) or start_time_clean.second != 0 or start_time_clean.microsecond != 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Appointments must start on the hour or half-hour (e.g. 09:00, 09:30).",
        )

    # 2. Past check
    if start_time_clean < now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot book an appointment in the past.",
        )

    # 3. 1-Hour minimum advance booking rule
    min_lead_time = now + timedelta(hours=settings.MIN_ADVANCE_BOOKING_HOURS)
    if start_time_clean < min_lead_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Appointments must be booked at least {settings.MIN_ADVANCE_BOOKING_HOURS} hour(s) in advance.",
        )

    # 4. Doctor existence & working hours check
    doc_result = await db.execute(select(Doctor).where(Doctor.id == doctor_id))
    doctor = doc_result.scalar_one_or_none()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doctor with ID {doctor_id} not found.",
        )

    day_of_week = start_time_clean.weekday()
    appt_time = start_time_clean.time()
    end_time_clean = start_time_clean + timedelta(minutes=settings.SLOT_DURATION_MINUTES)
    appt_end_time = end_time_clean.time()

    wh_result = await db.execute(
        select(DoctorWorkingHours).where(
            and_(
                DoctorWorkingHours.doctor_id == doctor_id,
                DoctorWorkingHours.day_of_week == day_of_week,
            )
        )
    )
    working_hours_list = wh_result.scalars().all()

    in_working_hours = False
    for wh in working_hours_list:
        if wh.start_time <= appt_time and appt_end_time <= wh.end_time:
            in_working_hours = True
            break

    if not in_working_hours:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Requested slot {start_time_clean.strftime('%H:%M')} falls outside Doctor {doctor.name}'s working hours for that day.",
        )

    # 5. Existing active booking check
    query = select(Appointment).where(
        and_(
            Appointment.doctor_id == doctor_id,
            Appointment.start_time == start_time_clean,
            Appointment.status == AppointmentStatus.BOOKED,
        )
    )
    if ignore_appointment_id is not None:
        query = query.where(Appointment.id != ignore_appointment_id)

    existing_result = await db.execute(query)
    existing_appt = existing_result.scalar_one_or_none()

    if existing_appt:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The requested appointment slot is already booked.",
        )

    return start_time_clean


async def create_appointment(db: AsyncSession, payload: AppointmentCreate) -> Appointment:
    # Check patient exists
    pat_result = await db.execute(select(Patient).where(Patient.id == payload.patient_id))
    patient = pat_result.scalar_one_or_none()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {payload.patient_id} not found.",
        )

    clean_start_time = await validate_slot(db, payload.doctor_id, payload.start_time)
    clean_end_time = clean_start_time + timedelta(minutes=settings.SLOT_DURATION_MINUTES)

    appointment = Appointment(
        doctor_id=payload.doctor_id,
        patient_id=payload.patient_id,
        start_time=clean_start_time,
        end_time=clean_end_time,
        status=AppointmentStatus.BOOKED,
        created_at=get_utc_now(),
        updated_at=get_utc_now(),
    )

    db.add(appointment)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The requested slot was just booked by another request.",
        )

    # Re-fetch appointment with relationships to avoid refresh concurrency lock issues
    res = await db.execute(select(Appointment).where(Appointment.id == appointment.id))
    return res.scalar_one()


async def cancel_appointment(
    db: AsyncSession, appointment_id: int, payload: AppointmentCancelRequest
) -> Appointment:
    result = await db.execute(select(Appointment).where(Appointment.id == appointment_id))
    appointment = result.scalar_one_or_none()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment with ID {appointment_id} not found.",
        )

    if appointment.status == AppointmentStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Appointment is already cancelled.",
        )

    appointment.status = AppointmentStatus.CANCELLED
    appointment.cancellation_reason = payload.reason
    appointment.updated_at = get_utc_now()

    await db.commit()
    res = await db.execute(select(Appointment).where(Appointment.id == appointment.id))
    return res.scalar_one()


async def reschedule_appointment(
    db: AsyncSession, appointment_id: int, payload: AppointmentRescheduleRequest
) -> Appointment:
    result = await db.execute(select(Appointment).where(Appointment.id == appointment_id))
    appointment = result.scalar_one_or_none()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment with ID {appointment_id} not found.",
        )

    if appointment.status == AppointmentStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot reschedule a cancelled appointment.",
        )

    clean_new_start = await validate_slot(
        db, appointment.doctor_id, payload.new_start_time, ignore_appointment_id=appointment.id
    )
    clean_new_end = clean_new_start + timedelta(minutes=settings.SLOT_DURATION_MINUTES)

    appointment.start_time = clean_new_start
    appointment.end_time = clean_new_end
    appointment.status = AppointmentStatus.BOOKED
    appointment.updated_at = get_utc_now()

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The new requested slot was just booked by another request.",
        )

    res = await db.execute(select(Appointment).where(Appointment.id == appointment.id))
    return res.scalar_one()


async def get_patient_upcoming_appointments(
    db: AsyncSession, patient_id: int
) -> List[Appointment]:
    # Check patient exists
    pat_result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = pat_result.scalar_one_or_none()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {patient_id} not found.",
        )

    now = get_utc_now()
    result = await db.execute(
        select(Appointment)
        .where(
            and_(
                Appointment.patient_id == patient_id,
                Appointment.start_time >= now,
                Appointment.status == AppointmentStatus.BOOKED,
            )
        )
        .order_by(Appointment.start_time.asc())
    )
    return result.scalars().all()
