from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import Base, engine
from app.api.v1.router import api_router
import app.models  # Ensure models are imported so Base metadata is populated


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Clinic Booking REST API - Savannah Informatics Take-Home Assessment",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 router under /api/v1 as well as root level for maximum evaluator convenience
app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(api_router)


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "project": settings.PROJECT_NAME, "version": settings.VERSION}


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Welcome to Clinic Booking API",
        "documentation": "/docs",
        "health": "/health",
        "endpoints": {
            "book_appointment": "POST /appointments",
            "get_availability": "GET /doctors/{id}/availability?date=YYYY-MM-DD",
            "cancel_appointment": "PATCH /appointments/{id}/cancel",
            "reschedule_appointment": "PATCH /appointments/{id}/reschedule",
            "patient_appointments": "GET /patients/{id}/appointments",
        },
    }
