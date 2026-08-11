"""CLV Prediction System — FastAPI Application Entry Point."""

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import predict, segments


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database tables on startup."""
    init_db()
    yield


app = FastAPI(
    title="CLV Prediction System",
    description="Customer Lifetime Value prediction and segmentation API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(predict.router, prefix="/api/v1", tags=["Predictions"])
app.include_router(segments.router, prefix="/api/v1", tags=["Segments"])


@app.get("/", tags=["Health"])
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy", "service": "CLV Prediction System"}


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
