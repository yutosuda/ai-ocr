"""
Main application entry point for the AI-OCR API service.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import api_router
from app.core.config import settings
from app.db.session import create_tables
from app.utils.logger import get_logger, add_request_id_to_response

# Initialize logger
logger = get_logger("main")

# Initialize FastAPI app
app = FastAPI(
    title="AI-OCR API",
    description="API service for AI-powered OCR and data extraction",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request ID middleware
app.middleware("http")(add_request_id_to_response)

# Include API router
app.include_router(api_router, prefix="/api/v1")

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    request_logger = getattr(request.state, "logger", logger)
    request_logger.exception(f"Unhandled exception: {exc}", exc=exc, path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again later."},
    )

@app.on_event("startup")
async def startup_event():
    """Initialize components on application startup."""
    logger.info("Initializing API service")
    await create_tables()
    logger.info("API service initialized successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on application shutdown."""
    logger.info("Shutting down API service")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"} 