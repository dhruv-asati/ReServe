"""
Health check endpoint.

Used by:
- Local developers verifying the server started correctly
- Uptime/monitoring checks
- Frontend developers confirming the backend is reachable before wiring up
  real features
"""

import logging

from fastapi import APIRouter

from app.core.config import get_settings
from app.db.database import check_database_connection
from app.schemas.common import HealthData, SuccessResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Health"])


@router.get(
    "/api/health",
    response_model=SuccessResponse[HealthData],
    summary="Health check",
    description="Returns API status, environment, version, and whether the "
    "configured PostgreSQL database is currently reachable.",
)
def health_check():
    settings = get_settings()
    db_connected = check_database_connection()

    if not db_connected:
        logger.warning("Health check: database is not reachable.")

    return SuccessResponse(
        data=HealthData(
            status="ok",
            environment=settings.ENVIRONMENT,
            version=settings.APP_VERSION,
            database_connected=db_connected,
        ),
        message="ReServe API is running.",
    )
