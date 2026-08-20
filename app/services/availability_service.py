from datetime import date, datetime, time, timedelta, timezone
from typing import List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.models.doctor import Doctor, DoctorWorkingHours
from app.models.appointment import Appointment, AppointmentStatus
from app.schemas.doctor import DoctorAvailabilityResponse, TimeSlot


async def get_doctor_availability(
    db: AsyncSession, doctor_id: int, target_date: date
) -> DoctorAvailabilityResponse:
    # 1. Fetch Doctor
    result = await db.execute(select(Doctor).where(Doctor.id == doctor_id))
    doctor = result.scalar_one_or_none()
    if not doctor:
        raise ValueError(f"Doctor with ID {doctor_id} not found.")

    # 2. Get day of week (0 = Monday, 6 = Sunday)
    day_of_week = target_date.weekday()

    # 3. Find doctor working hours for this day of week
    wh_result = await db.execute(
        select(DoctorWorkingHours).where(
            and_(
                DoctorWorkingHours.doctor_id == doctor_id,
                DoctorWorkingHours.day_of_week == day_of_week,
            )
        )
    )
    working_hours = wh_result.scalars().all()

    if not working_hours:
        return DoctorAvailabilityResponse(
            doctor_id=doctor.id,
            doctor_name=doctor.name,
            date=target_date,
            available_slots=[],
        )

    # 4. Fetch existing BOOKED appointments for this doctor on target_date
    start_of_day = datetime.combine(target_date, time.min)
    end_of_day = datetime.combine(target_date, time.max)

    appts_result = await db.execute(
        select(Appointment).where(
            and_(
                Appointment.doctor_id == doctor_id,
                Appointment.status == AppointmentStatus.BOOKED,
                Appointment.start_time >= start_of_day,
                Appointment.start_time <= end_of_day,
            )
        )
    )
    booked_appointments = appts_result.scalars().all()
    booked_start_times = {
        appt.start_time.replace(tzinfo=None) if appt.start_time.tzinfo else appt.start_time
        for appt in booked_appointments
    }

    # 5. Generate 30-minute slots within doctor's working hours
    available_slots: List[TimeSlot] = []
    slot_duration = timedelta(minutes=settings.SLOT_DURATION_MINUTES)
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

    for wh in working_hours:
        current_dt = datetime.combine(target_date, wh.start_time)
        end_dt = datetime.combine(target_date, wh.end_time)

        while current_dt + slot_duration <= end_dt:
            slot_end = current_dt + slot_duration
            
            # Slot is unavailable if already booked or in the past
            is_booked = current_dt in booked_start_times
            is_past = (target_date == now_utc.date() and current_dt < now_utc)

            if not is_booked and not is_past:
                available_slots.append(
                    TimeSlot(
                        start_time=current_dt.isoformat(),
                        end_time=slot_end.isoformat(),
                        is_available=True,
                    )
                )

            current_dt += slot_duration

    return DoctorAvailabilityResponse(
        doctor_id=doctor.id,
        doctor_name=doctor.name,
        date=target_date,
        available_slots=available_slots,
    )
