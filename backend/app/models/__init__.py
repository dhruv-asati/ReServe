"""
Importing this package registers every ORM model on Base.metadata, which is
what Alembic's autogenerate (and Base.metadata.create_all, if ever used)
relies on. Import app.models — not individual submodules — anywhere you
need the full schema available (e.g. alembic/env.py, seed scripts).
"""

from app.models.allocation import Allocation
from app.models.match import Match
from app.models.notification import Notification
from app.models.operation import OperationEvent, RescueOperation
from app.models.prediction import Prediction
from app.models.recipient import Recipient
from app.models.resource import Resource
from app.models.resource_request import ResourceRequest, ResourceRequestStatusHistory
from app.models.rescue_hub import RescueHub
from app.models.rescue_partner import RescuePartner
from app.models.rescue_request import RescueRequest
from app.models.user import User

__all__ = [
    "Allocation",
    "Match",
    "Notification",
    "OperationEvent",
    "RescueOperation",
    "Prediction",
    "Recipient",
    "Resource",
    "ResourceRequest",
    "ResourceRequestStatusHistory",
    "RescueHub",
    "RescuePartner",
    "RescueRequest",
    "User",
]
