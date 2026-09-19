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

from app.api import admin, allocations, analytics, auth, health, matching, notifications, operations, predictions, recipients, requests, rescue_partners, resources, uploads, users
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.logging_config import configure_logging

settings = get_settings()

configure_logging()
logger = logging.getLogger(__name__)

# --- Swagger tag organization ----------------------------------------------
# Purely metadata: gives each router's tag a description and fixes the
# order tags/endpoints are grouped in under /docs (FastAPI otherwise sorts
# tags by first-appearance, which is fragile as routers get reordered).
# Every name here must match a `tags=[...]` value used by an APIRouter in
# app/api/*.py.
openapi_tags = [
    {
        "name": "Health",
        "description": "Uptime/readiness check. No authentication required.",
    },
    {
        "name": "Auth",
        "description": (
            "Register, log in, and manage JWT access/refresh tokens. See the "
            "'Authentication & roles' section of the backend README for the full "
            "picture — in short: log in here, then click **Authorize** in Swagger "
            "UI and paste the `access_token` to call any protected endpoint below."
        ),
    },
    {
        "name": "Users",
        "description": "Read and update the authenticated user's own account, or (ADMIN) any account.",
    },
    {
        "name": "Resources",
        "description": (
            "Surplus FOOD/MEDICAL resources posted by providers. Create/edit/delete is "
            "restricted to the resource's own PROVIDER or an ADMIN."
        ),
    },
    {
        "name": "Uploads",
        "description": "Upload/delete resource images (Supabase Storage, or local disk in dev).",
    },
    {
        "name": "Recipients",
        "description": "Recipient organization profiles that request resources.",
    },
    {
        "name": "Rescue Partners",
        "description": "Rescue-partner organization profiles that handle pickup/delivery.",
    },
    {
        "name": "Resource Requests",
        "description": "Recipients requesting a specific resource, and providers accepting/declining.",
    },
    {
        "name": "Matching",
        "description": "AI/rule-based matching of resources to recipients and rescue partners.",
    },
    {
        "name": "Allocations",
        "description": "Confirmed resource-to-recipient assignments created from a match.",
    },
    {
        "name": "Operations",
        "description": "Pickup/delivery lifecycle tracking for an allocation (rescue partner facing).",
    },
    {
        "name": "Analytics",
        "description": "Aggregate stats across resources, allocations, and operations.",
    },
    {
        "name": "Predictions",
        "description": "Forecasts (e.g. expected surplus) derived from historical data.",
    },
    {
        "name": "Notifications",
        "description": "In-app notifications for the authenticated user.",
    },
    {
        "name": "Admin",
        "description": "ADMIN-only account/verification management. Every endpoint requires the ADMIN role.",
    },
]

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "ReServe — AI-Powered Resource Redistribution & Rescue Network.\n\n"
        "Backend API only. Turning surplus into timely service.\n\n"
        "All endpoints (except `/api/health` and `/api/auth/*`) require a bearer access "
        "token — log in via **Auth &rarr; POST /api/auth/login**, then click **Authorize** "
        "above and paste the `access_token`. See the backend README for the full "
        "authentication and roles reference."
    ),
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=openapi_tags,
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
app.include_router(matching.router)
app.include_router(allocations.router)
app.include_router(operations.router)
app.include_router(analytics.router)
app.include_router(predictions.router)
app.include_router(notifications.router)
app.include_router(admin.router)


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
