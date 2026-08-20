import uuid
import pytest
import pytest_asyncio
from datetime import time
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.core.database import Base, AsyncSessionLocal, engine, get_db
from app.models.appointment import Appointment
from app.models.doctor import Doctor, DoctorWorkingHours
from app.models.patient import Patient


async def _wipe_tables():
    async with AsyncSessionLocal() as session:
        await session.execute(delete(Appointment))
        await session.execute(delete(DoctorWorkingHours))
        await session.execute(delete(Doctor))
        await session.execute(delete(Patient))
        await session.commit()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database_schema():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest_asyncio.fixture(autouse=True)
async def clean_database():
    await _wipe_tables()
    yield
    await _wipe_tables()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with AsyncSessionLocal() as session:
            try:
                yield session
            finally:
                await session.close()

    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test/api/v1") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def seed_data(db_session: AsyncSession):
    uid = uuid.uuid4().hex[:6]
    # Seed Doctor with unique email per test
    doctor = Doctor(name="Dr. Test Specialist", email=f"test.doctor.{uid}@clinic.com", specialization="General")
    db_session.add(doctor)
    await db_session.flush()

    # Mon-Sun working hours (09:00 - 17:00)
    for day in range(7):
        wh = DoctorWorkingHours(doctor_id=doctor.id, day_of_week=day, start_time=time(9, 0), end_time=time(17, 0))
        db_session.add(wh)

    # Seed Patient with unique email per test
    patient = Patient(name="Test Patient", email=f"patient.{uid}@test.com", phone="+1234567890")
    db_session.add(patient)

    await db_session.commit()
    await db_session.refresh(doctor)
    await db_session.refresh(patient)
    return {"doctor": doctor, "patient": patient}
