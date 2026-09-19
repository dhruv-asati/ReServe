"""
Predictions endpoint:

    GET /api/predictions

Historical resource totals, most common resource categories, and basic
demand trends, computed from the database. Falls back to a clearly
labeled demo response when there isn't enough recorded activity. Purely
informational and read-only — it feeds nothing into matching or
allocation. Open to any authenticated user, same as /api/analytics.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.predictions import PredictionsData
from app.services import prediction_service

router = APIRouter(prefix="/api/predictions", tags=["Predictions"])


@router.get(
    "",
    response_model=SuccessResponse[PredictionsData],
    summary="Basic resource predictions",
    description=(
        "Returns historical resource totals, the most common resource categories, and basic "
        "demand trends (requested quantity, later half of the window vs. earlier half), computed "
        "from the database over the last `days` days (rounded up to whole weeks). If there isn't "
        "enough recorded data, a demo response is returned instead, clearly labeled with "
        "`is_demo: true` and `data_source: \"DEMO\"`. Read-only: does not affect matching or "
        "allocation. Available to any authenticated user."
    ),
)
def get_predictions(
    days: int = Query(default=90, ge=28, le=365, description="How many days of history to analyze (28-365)."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = prediction_service.get_predictions(db, days)
    if data.is_demo:
        message = "Not enough data for a real prediction — returning a clearly labeled DEMO response."
    else:
        message = f"Predictions generated from {data.data_sufficiency.resources_found} resource(s) and {data.data_sufficiency.requests_found} request(s)."
    return SuccessResponse(data=data, message=message)
