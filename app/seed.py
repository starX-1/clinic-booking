import asyncio
from datetime import time
from sqlalchemy import select
from app.core.database import AsyncSessionLocal, Base, engine
from app.models.doctor import Doctor, DoctorWorkingHours
from app.models.patient import Patient


async def seed_data():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # Check if doctors already exist
        result = await session.execute(select(Doctor))
        existing_doctors = result.scalars().all()
        if existing_doctors:
            print("Database already contains doctor records. Skipping seeding.")
            return

        print("Seeding database with 5 doctors and working hours...")

        # 5 Doctors
        doctors_data = [
            {
                "name": "Dr. Sarah Kimani",
                "email": "sarah.kimani@clinic.co.ke",
                "specialization": "General Practitioner",
            },
            {
                "name": "Dr. David Ochieng",
                "email": "david.ochieng@clinic.co.ke",
                "specialization": "Pediatrician",
            },
            {
                "name": "Dr. Amina Hassan",
                "email": "amina.hassan@clinic.co.ke",
                "specialization": "Dermatologist",
            },
            {
                "name": "Dr. John Mutua",
                "email": "john.mutua@clinic.co.ke",
                "specialization": "Cardiologist",
            },
            {
                "name": "Dr. Grace Wambui",
                "email": "grace.wambui@clinic.co.ke",
                "specialization": "Gynecologist",
            },
        ]

        # Standard Working Hours: Mon-Fri (0-4), 09:00 - 17:00
        for doc_info in doctors_data:
            doctor = Doctor(
                name=doc_info["name"],
                email=doc_info["email"],
                specialization=doc_info["specialization"],
            )
            session.add(doctor)
            await session.flush()  # get doctor.id

            # Add working hours Mon-Fri 09:00 - 17:00
            for day in range(5):  # 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri
                wh = DoctorWorkingHours(
                    doctor_id=doctor.id,
                    day_of_week=day,
                    start_time=time(9, 0),
                    end_time=time(17, 0),
                )
                session.add(wh)

        # Seed sample patients
        patients_data = [
            {"name": "Alice Njeri", "email": "alice.njeri@example.com", "phone": "+254712345678"},
            {"name": "Brian Kiprop", "email": "brian.kiprop@example.com", "phone": "+254722987654"},
        ]

        for pat_info in patients_data:
            patient = Patient(name=pat_info["name"], email=pat_info["email"], phone=pat_info["phone"])
            session.add(patient)

        await session.commit()
        print("Successfully seeded 5 doctors, working hours, and sample patients!")


if __name__ == "__main__":
    asyncio.run(seed_data())
