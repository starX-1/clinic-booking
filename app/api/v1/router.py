from fastapi import APIRouter
from app.api.v1.endpoints import appointments, doctors, patients

api_router = APIRouter()

api_router.include_router(appointments.router)
api_router.include_router(doctors.router)
api_router.include_router(patients.router)
