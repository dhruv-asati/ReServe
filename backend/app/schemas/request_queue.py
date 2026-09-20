"""
Row shape for the Rescue Requests page queues:

    GET /api/requests/incoming
    GET /api/requests/outgoing
    GET /api/requests/completed

camelCase and display-oriented on purpose (see frontend/src/data/requests.js):
`quantity`, `deadline` and `created` are pre-formatted strings the page
renders as-is. The raw ISO timestamps are included alongside for anything
that needs to sort or reformat in the browser's own timezone.
"""

from datetime import datetime

from pydantic import BaseModel


class RequestRowOut(BaseModel):
    id: str
    resource: str
    resourceType: str  # "food" | "medical"
    quantity: str
    provider: str
    recipient: str
    location: str
    deadline: str
    status: str  # a value from the frontend's STATUS vocabulary (utils/theme.js)
    created: str
    description: str
    deadlineAt: datetime
    createdAt: datetime
