"""
ReServe API — application entrypoint.

App wiring, CORS, logging, Swagger docs, error handling, and router
mounting. Routers are include_router()'d here as each stage adds them,
without touching anything already working.
"""

import logging
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import auth, health, recipients, requests, rescue_partners, resources, uploads, users
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.logging_config import configure_logging

settings = get_settings()

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "ReServe — AI-Powered Resource Redistribution & Rescue Network.\n\n"
        "Backend API only. Turning surplus into timely service."
    ),
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# --- CORS ---------------------------------------------------------------
# Allows the separately-developed React frontend (e.g. Vite dev server on
# localhost:5173, or CRA on localhost:3000) to call this API from the
# browser. Origins are configurable via CORS_ORIGINS in .env so this works
# the same way in local dev and in deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Local upload storage --------------------------------------------------
# Serves files written by the local-disk storage backend (used whenever
# SUPABASE_URL/SUPABASE_KEY aren't configured — see
# app/services/storage_service.py) so a resource's image_url still resolves
# to something loadable in local development with no Supabase project set
# up. The directory must exist before StaticFiles will mount it.
Path(settings.LOCAL_UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
app.mount("/static/uploads", StaticFiles(directory=settings.LOCAL_UPLOAD_DIR), name="uploads")


# --- Secure error handling ------------------------------------------------
# Never leak stack traces or internal exception details to API clients.
# Everything is normalized to the {"success": false, "error": {...}} envelope.


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    logger.info("AppError on %s %s: [%s] %s", request.method, request.url.path, exc.code, exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
            },
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": "HTTP_ERROR",
                "message": str(exc.detail),
            },
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.info("Validation error on %s %s: %s", request.method, request.url.path, exc.errors())
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "One or more fields failed validation.",
                "details": exc.errors(),
            },
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred.",
            },
        },
    )


# --- Routers --------------------------------------------------------------
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(resources.router)
app.include_router(uploads.router)
app.include_router(recipients.router)
app.include_router(rescue_partners.router)
app.include_router(requests.router)


@app.on_event("startup")
def on_startup():
    logger.info(
        "%s v%s starting up in '%s' mode.",
        settings.APP_NAME,
        settings.APP_VERSION,
        settings.ENVIRONMENT,
    )
    logger.info("CORS origins allowed: %s", settings.cors_origins_list)


@app.on_event("shutdown")
def on_shutdown():
    logger.info("%s shutting down.", settings.APP_NAME)
