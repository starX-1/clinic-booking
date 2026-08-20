import pytest
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient


def get_next_weekday(days_ahead: int = 1) -> datetime:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    dt = now + timedelta(days=days_ahead)
    if dt.weekday() == 5:
        dt += timedelta(days=2)
    elif dt.weekday() == 6:
        dt += timedelta(days=1)
    return dt


@pytest.mark.asyncio
async def test_get_patient_upcoming_appointments_bonus(client: AsyncClient, seed_data: dict):
    doctor = seed_data["doctor"]
    patient = seed_data["patient"]

    dt1 = get_next_weekday(2).replace(hour=10, minute=0, second=0, microsecond=0)
    dt2 = get_next_weekday(3).replace(hour=14, minute=0, second=0, microsecond=0)

    res1 = await client.post(
        "/appointments",
        json={"doctor_id": doctor.id, "patient_id": patient.id, "start_time": dt1.isoformat() + "Z"},
    )
    assert res1.status_code == 201

    res2 = await client.post(
        "/appointments",
        json={"doctor_id": doctor.id, "patient_id": patient.id, "start_time": dt2.isoformat() + "Z"},
    )
    assert res2.status_code == 201

    # Fetch patient appointments
    res = await client.get(f"/patients/{patient.id}/appointments")
    assert res.status_code == 200
    data = res.json()

    assert len(data) == 2
    # Verify sorted chronologically
    assert data[0]["start_time"] < data[1]["start_time"]
