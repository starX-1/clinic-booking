import pytest
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient


def get_next_weekday(days_ahead: int = 1):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    dt = now + timedelta(days=days_ahead)
    if dt.weekday() == 5:
        dt += timedelta(days=2)
    elif dt.weekday() == 6:
        dt += timedelta(days=1)
    return dt.date()


@pytest.mark.asyncio
async def test_get_doctor_availability_success(client: AsyncClient, seed_data: dict):
    doctor = seed_data["doctor"]
    target_date = get_next_weekday(2).isoformat()

    response = await client.get(f"/doctors/{doctor.id}/availability?date={target_date}")
    assert response.status_code == 200
    data = response.json()

    assert data["doctor_id"] == doctor.id
    assert data["doctor_name"] == doctor.name
    # 09:00 to 17:00 is 8 hours = 16 thirty-minute slots
    assert len(data["available_slots"]) == 16
    assert data["available_slots"][0]["is_available"] is True


@pytest.mark.asyncio
async def test_get_doctor_availability_not_found(client: AsyncClient):
    response = await client.get("/doctors/99999/availability?date=2026-08-25")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
