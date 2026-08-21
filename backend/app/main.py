"""CLV Prediction System — FastAPI Application Entry Point."""

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import predict, segments, customers


# ---------------------------------------------------------
# Application Lifespan
# ---------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database tables when the application starts."""

    init_db()

    yield


# ---------------------------------------------------------
# FastAPI Application
# ---------------------------------------------------------

app = FastAPI(
    title="CLV Prediction System",
    description=(
        "Customer Lifetime Value prediction, "
        "customer segmentation and Customer 360 API"
    ),
    version="1.1.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------
# CORS Configuration
# ---------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# API Routers
# ---------------------------------------------------------

app.include_router(
    predict.router,
    prefix="/api/v1",
    tags=["Predictions"],
)

app.include_router(
    segments.router,
    prefix="/api/v1",
    tags=["Segments"],
)

app.include_router(
    customers.router,
    prefix="/api/v1",
    tags=["Customers"],
)


# ---------------------------------------------------------
# Health Check
# ---------------------------------------------------------

@app.get("/", tags=["Health"])
async def health_check() -> dict:
    """Check whether the CLV API is running."""

    return {
        "status": "healthy",
        "service": "CLV Prediction System",
        "version": "1.1.0",
    }


# ---------------------------------------------------------
# Local Development Server
# ---------------------------------------------------------

if __name__ == "__main__":

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )