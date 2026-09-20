"""
Request-queue service: the three tabs of the Rescue Requests page, built
from ResourceRequest rows (a recipient's demand-side ask for a quantity of
FOOD or MEDICAL supplies).

    outgoing   requests the caller's own recipient organization has raised
               that are still open (PENDING / APPROVED)
    incoming   open requests raised by *other* organizations — what a
               PROVIDER / RESCUE_PARTNER / ADMIN can act on. RECIPIENT
               accounts never see other organizations' requests, so their
               incoming queue is always empty (same visibility rule as
               GET /api/requests)
    completed  requests in a final state (FULFILLED / REJECTED / CANCELLED),
               scoped like GET /api/requests: RECIPIENTs see their own,
               everyone else sees all

Read-only. A ResourceRequest is deliberately not linked to a specific
Resource or provider yet (see ResourceRequestStatus in models/enums.py), so
`provider` reads "Not assigned" until that matching work exists.
"""

from datetime import datetime, timedelta, timezone
from typing import Literal

from sqlalchemy.orm import Session, joinedload

from app.models.enums import ResourceRequestStatus, UserRole
from app.models.recipient import Recipient
from app.models.resource_request import ResourceRequest
from app.models.user import User
from app.schemas.request_queue import RequestRowOut

Tab = Literal["incoming", "outgoing", "completed"]

OPEN_STATUSES = (ResourceRequestStatus.PENDING, ResourceRequestStatus.APPROVED)
CLOSED_STATUSES = (
    ResourceRequestStatus.FULFILLED,
    ResourceRequestStatus.REJECTED,
    ResourceRequestStatus.CANCELLED,
)

# ResourceRequestStatus -> the frontend's lowercase STATUS vocabulary. The
# frontend has no "rejected" status, so a rejected request shows as cancelled.
_STATUS_MAP = {
    ResourceRequestStatus.PENDING: "pending",
    ResourceRequestStatus.APPROVED: "matched",
    ResourceRequestStatus.FULFILLED: "delivered",
    ResourceRequestStatus.REJECTED: "cancelled",
    ResourceRequestStatus.CANCELLED: "cancelled",
}


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _when_text(dt: datetime, now: datetime) -> str:
    """'Today, 6:00 PM UTC' / 'Tomorrow, 9:00 AM UTC' / '20 Sep, 6:00 PM UTC' (server time is UTC)."""
    dt = _aware(dt).astimezone(timezone.utc)
    day_delta = (dt.date() - now.date()).days
    clock = f"{dt.hour % 12 or 12}:{dt.minute:02d} {'AM' if dt.hour < 12 else 'PM'} UTC"
    if day_delta == 0:
        return f"Today, {clock}"
    if day_delta == 1:
        return f"Tomorrow, {clock}"
    if day_delta == -1:
        return f"Yesterday, {clock}"
    return f"{dt.day} {dt:%b}, {clock}"


def _own_recipient_id(db: Session, user: User):
    return db.query(Recipient.id).filter(Recipient.user_id == user.id).scalar()


def _to_row(request: ResourceRequest, now: datetime) -> RequestRowOut:
    resource_type = request.resource_type.value.lower()
    recipient = request.recipient
    return RequestRowOut(
        id=str(request.id),
        resource=f"{resource_type.title()} request",
        resourceType=resource_type,
        quantity=f"{float(request.requested_quantity):g} units",
        provider="Not assigned",
        recipient=request.requesting_organization,
        location=recipient.location_address if recipient is not None else "",
        deadline=_when_text(request.needed_by, now),
        status=_STATUS_MAP[request.status],
        created=_when_text(request.created_at, now),
        description=request.notes or request.eligibility_requirements or "",
        deadlineAt=_aware(request.needed_by),
        createdAt=_aware(request.created_at),
    )


def get_queue(db: Session, current_user: User, tab: Tab, limit: int = 100) -> list[RequestRowOut]:
    query = db.query(ResourceRequest).options(joinedload(ResourceRequest.recipient))
    own_id = _own_recipient_id(db, current_user)
    is_recipient = current_user.role == UserRole.RECIPIENT

    if tab == "outgoing":
        if own_id is None:
            return []
        query = query.filter(ResourceRequest.recipient_id == own_id, ResourceRequest.status.in_(OPEN_STATUSES))
    elif tab == "incoming":
        if is_recipient:
            return []
        query = query.filter(ResourceRequest.status.in_(OPEN_STATUSES))
        if own_id is not None:
            query = query.filter(ResourceRequest.recipient_id != own_id)
    else:  # completed
        query = query.filter(ResourceRequest.status.in_(CLOSED_STATUSES))
        if is_recipient:
            if own_id is None:
                return []
            query = query.filter(ResourceRequest.recipient_id == own_id)

    now = datetime.now(timezone.utc)
    requests = query.order_by(ResourceRequest.created_at.desc()).limit(limit).all()
    return [_to_row(request, now) for request in requests]
