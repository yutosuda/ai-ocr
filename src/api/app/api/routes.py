"""
Main API router that combines all API route modules.
"""
from fastapi import APIRouter

from app.api.endpoints import documents, jobs, extractions

# Create the main API router
api_router = APIRouter()

# Include specific route modules
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(extractions.router, prefix="/extractions", tags=["extractions"]) 