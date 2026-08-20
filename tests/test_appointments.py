import pytest
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient


def get_next_weekday(days_ahead: int = 1) -> datetime:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    dt = now + timedelta(days=days_ahead)
    # If weekend (Sat=5, Sun=6), move to Monday
    if dt.weekday() == 5:
        dt += timedelta(days=2)
    elif dt.weekday() == 6:
        dt += timedelta(days=1)
    return dt


@pytest.mark.asyncio
async def test_book_appointment_success(client: AsyncClient, seed_data: dict):
    doctor = seed_data["doctor"]
    patient = seed_data["patient"]

    future_dt = get_next_weekday(2).replace(hour=10, minute=0, second=0, microsecond=0)
    payload = {
        "doctor_id": doctor.id,
        "patient_id": patient.id,
        "start_time": future_dt.isoformat() + "Z",
    }

    response = await client.post("/appointments", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["doctor_id"] == doctor.id
    assert data["patient_id"] == patient.id
    assert data["status"] == "BOOKED"


@pytest.mark.asyncio
async def test_book_appointment_past_date_fails(client: AsyncClient, seed_data: dict):
    doctor = seed_data["doctor"]
    patient = seed_data["patient"]

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    past_dt = (now - timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
    payload = {
        "doctor_id": doctor.id,
        "patient_id": patient.id,
        "start_time": past_dt.isoformat() + "Z",
    }

    response = await client.post("/appointments", json=payload)
    assert response.status_code == 400
    assert "past" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_book_appointment_outside_working_hours_fails(client: AsyncClient, seed_data: dict):
    doctor = seed_data["doctor"]
    patient = seed_data["patient"]

    # 18:00 (outside 09:00 - 17:00)
    outside_dt = get_next_weekday(2).replace(hour=18, minute=0, second=0, microsecond=0)
    payload = {
        "doctor_id": doctor.id,
        "patient_id": patient.id,
        "start_time": outside_dt.isoformat() + "Z",
    }

    response = await client.post("/appointments", json=payload)
    assert response.status_code == 400
    assert "working hours" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_book_appointment_double_booking_conflict(client: AsyncClient, seed_data: dict):
    doctor = seed_data["doctor"]
    patient = seed_data["patient"]

    future_dt = get_next_weekday(2).replace(hour=11, minute=0, second=0, microsecond=0)
    payload = {
        "doctor_id": doctor.id,
        "patient_id": patient.id,
        "start_time": future_dt.isoformat() + "Z",
    }

    # First booking
    res1 = await client.post("/appointments", json=payload)
    assert res1.status_code == 201

    # Second booking for exact same slot
    res2 = await client.post("/appointments", json=payload)
    assert res2.status_code == 409
    assert "already booked" in res2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_cancel_appointment_success_and_slot_freed(client: AsyncClient, seed_data: dict):
    doctor = seed_data["doctor"]
    patient = seed_data["patient"]

    future_dt = get_next_weekday(2).replace(hour=14, minute=0, second=0, microsecond=0)
    payload = {
        "doctor_id": doctor.id,
        "patient_id": patient.id,
        "start_time": future_dt.isoformat() + "Z",
    }

    res = await client.post("/appointments", json=payload)
    assert res.status_code == 201
    appt_id = res.json()["id"]

    # Cancel appointment
    cancel_res = await client.patch(
        f"/appointments/{appt_id}/cancel",
        json={"reason": "Scheduling conflict with work"},
    )
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "CANCELLED"
    assert cancel_res.json()["cancellation_reason"] == "Scheduling conflict with work"

    # Verify attempting to cancel again returns 400 Bad Request
    re_cancel_res = await client.patch(
        f"/appointments/{appt_id}/cancel",
        json={"reason": "Duplicate cancellation request"},
    )
    assert re_cancel_res.status_code == 400
    assert "already cancelled" in re_cancel_res.json()["detail"].lower()

    # Verify slot is bookable again
    rebook_res = await client.post("/appointments", json=payload)
    assert rebook_res.status_code == 201


@pytest.mark.asyncio
async def test_reschedule_appointment_success(client: AsyncClient, seed_data: dict):
    doctor = seed_data["doctor"]
    patient = seed_data["patient"]

    initial_dt = get_next_weekday(2).replace(hour=15, minute=0, second=0, microsecond=0)
    payload = {
        "doctor_id": doctor.id,
        "patient_id": patient.id,
        "start_time": initial_dt.isoformat() + "Z",
    }

    res = await client.post("/appointments", json=payload)
    assert res.status_code == 201
    appt_id = res.json()["id"]

    new_dt = get_next_weekday(2).replace(hour=16, minute=0, second=0, microsecond=0)
    reschedule_res = await client.patch(
        f"/appointments/{appt_id}/reschedule",
        json={"new_start_time": new_dt.isoformat() + "Z"},
    )
    assert reschedule_res.status_code == 200
    assert reschedule_res.json()["status"] == "BOOKED"

    # Verify original slot (15:00) is now bookable again
    orig_rebook = await client.post("/appointments", json=payload)
    assert orig_rebook.status_code == 201
