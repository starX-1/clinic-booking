import asyncio
import pytest
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_concurrent_booking_race_condition_protection(client: AsyncClient, seed_data: dict):
    doctor = seed_data["doctor"]
    patient = seed_data["patient"]

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    # Ensure target day is a weekday (Monday = 0)
    days_ahead = (0 - now.weekday() + 7) % 7
    if days_ahead == 0:
        days_ahead = 7
    target_date = now + timedelta(days=days_ahead)
    future_dt = target_date.replace(hour=10, minute=30, second=0, microsecond=0)

    payload = {
        "doctor_id": doctor.id,
        "patient_id": patient.id,
        "start_time": future_dt.isoformat() + "Z",
    }

    # Simulate 5 concurrent booking requests for the exact same slot
    tasks = [client.post("/appointments", json=payload) for _ in range(5)]
    responses = await asyncio.gather(*tasks, return_exceptions=False)

    status_codes = [r.status_code for r in responses]

    # Exactly ONE request should succeed (201 Created), and all others must fail with conflict (409 Conflict)
    assert status_codes.count(201) == 1
    assert status_codes.count(409) == 4
