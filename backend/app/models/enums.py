"""
Shared enums used across ReServe's database models.

These are used both as SQLAlchemy column types (creating native Postgres
ENUM types via values_callable so the DB stores plain strings like
"FOOD" rather than Python repr) and can be reused directly in Pydantic
schemas later.
"""

import enum


class UserRole(str, enum.Enum):
    PROVIDER = "PROVIDER"
    RECIPIENT = "RECIPIENT"
    RESCUE_PARTNER = "RESCUE_PARTNER"
    ADMIN = "ADMIN"


class ResourceType(str, enum.Enum):
    FOOD = "FOOD"
    MEDICAL = "MEDICAL"


class ResourceStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    MATCHING = "MATCHING"
    ALLOCATED = "ALLOCATED"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class UrgencyLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class FoodCategory(str, enum.Enum):
    """Food-specific subtype. Only meaningful when Resource.resource_type
    is FOOD — kept separate from the free-text `category` column, which
    is used for both FOOD and MEDICAL resources."""

    COOKED_MEALS = "COOKED_MEALS"
    RAW_PRODUCE = "RAW_PRODUCE"
    BAKERY = "BAKERY"
    DAIRY = "DAIRY"
    GRAINS_CEREALS = "GRAINS_CEREALS"
    PACKAGED_SNACKS = "PACKAGED_SNACKS"
    BEVERAGES = "BEVERAGES"
    FROZEN_FOOD = "FROZEN_FOOD"
    CANNED_GOODS = "CANNED_GOODS"
    OTHER = "OTHER"


class AllergenType(str, enum.Enum):
    """The FDA/FSSAI-style major allergen categories, plus NONE for
    resources explicitly confirmed allergen-free. NONE should not be
    combined with any other value in the same list."""

    MILK = "MILK"
    EGGS = "EGGS"
    FISH = "FISH"
    SHELLFISH = "SHELLFISH"
    TREE_NUTS = "TREE_NUTS"
    PEANUTS = "PEANUTS"
    WHEAT_GLUTEN = "WHEAT_GLUTEN"
    SOY = "SOY"
    SESAME = "SESAME"
    NONE = "NONE"


class StorageRequirement(str, enum.Enum):
    REFRIGERATED = "REFRIGERATED"
    FROZEN = "FROZEN"
    ROOM_TEMPERATURE = "ROOM_TEMPERATURE"
    DRY_STORAGE = "DRY_STORAGE"


class RecipientType(str, enum.Enum):
    NGO = "NGO"
    SHELTER = "SHELTER"
    COMMUNITY_ORG = "COMMUNITY_ORG"
    MEDICAL_ORG = "MEDICAL_ORG"


class PartnerType(str, enum.Enum):
    VOLUNTEER = "VOLUNTEER"
    TRANSPORT_ORG = "TRANSPORT_ORG"
    ORGANIZATION = "ORGANIZATION"


class RescueRequestStatus(str, enum.Enum):
    PENDING = "PENDING"
    MATCHING = "MATCHING"
    MATCHED = "MATCHED"
    PARTIALLY_MATCHED = "PARTIALLY_MATCHED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class ResourceRequestStatus(str, enum.Enum):
    """
    Status of a ResourceRequest — a RECIPIENT's demand-side ask for a
    quantity of some resource type, independent of any specific Resource.

    Distinct from RescueRequestStatus above: that one tracks the
    matching-engine's *supply-side* coordination record for a specific
    posted Resource. This one tracks a recipient's request for help,
    reviewed by providers/admins, before any specific resource is
    involved. Deliberately not wired to each other (yet) — connecting a
    ResourceRequest to a matched Resource/RescueRequest is matching-engine
    work for a later stage.
    """

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    FULFILLED = "FULFILLED"
    CANCELLED = "CANCELLED"


class MatchCandidateType(str, enum.Enum):
    RECIPIENT = "RECIPIENT"
    RESCUE_HUB = "RESCUE_HUB"


class MatchStatus(str, enum.Enum):
    PROPOSED = "PROPOSED"
    SELECTED = "SELECTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class AllocationStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    REALLOCATED = "REALLOCATED"
    CANCELLED = "CANCELLED"
    DELIVERED = "DELIVERED"


class OperationStatus(str, enum.Enum):
    CREATED = "CREATED"
    MATCHING = "MATCHING"
    MATCHED = "MATCHED"
    PARTNER_ASSIGNED = "PARTNER_ASSIGNED"
    PICKUP_IN_PROGRESS = "PICKUP_IN_PROGRESS"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    REALLOCATING = "REALLOCATING"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class OperationEventType(str, enum.Enum):
    CREATED = "CREATED"
    MATCHING_STARTED = "MATCHING_STARTED"
    MATCHED = "MATCHED"
    PARTNER_ASSIGNED = "PARTNER_ASSIGNED"
    PICKUP_STARTED = "PICKUP_STARTED"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    REALLOCATION_TRIGGERED = "REALLOCATION_TRIGGERED"
    REALLOCATED = "REALLOCATED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    NOTE = "NOTE"


class NotificationType(str, enum.Enum):
    MATCH_FOUND = "MATCH_FOUND"
    PARTNER_ASSIGNED = "PARTNER_ASSIGNED"
    OPERATION_UPDATE = "OPERATION_UPDATE"
    REALLOCATION = "REALLOCATION"
    DELIVERY_CONFIRMED = "DELIVERY_CONFIRMED"
    SYSTEM = "SYSTEM"
