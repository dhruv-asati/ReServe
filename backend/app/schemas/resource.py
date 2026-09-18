"""
Pydantic schemas for the Resource CRUD endpoints.

Food and medical resources share one table (see app/models/resource.py),
differentiated by `resource_type` plus a couple of fields that behave
differently per type: `requires_medical_verification` is force-set by the
service layer for MEDICAL resources regardless of what's posted, and
`category` is where type-specific detail lives ("vegetarian meals" vs.
"amoxicillin 500mg") rather than separate tables — practical for a
hackathon schema while still keeping the two domains distinguishable.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import AllergenType, FoodCategory, ResourceStatus, ResourceType, StorageRequirement, UrgencyLevel
from app.schemas.analysis import ResourceAnalysisResult

# All food-specific fields, used by _validate_food_fields to check
# type-appropriateness generically instead of listing each one by hand.
_FOOD_FIELD_NAMES = (
    "food_category",
    "is_vegetarian",
    "preparation_time",
    "allergen_info",
    "storage_requirements",
    "packaging_info",
)


def _check_date_relationships(
    *,
    available_time: Optional[datetime],
    expiry_time: Optional[datetime],
    pickup_window_start: Optional[datetime],
    pickup_window_end: Optional[datetime],
    preparation_time: Optional[datetime] = None,
) -> None:
    """
    Shared cross-field date validation for both create and update payloads.
    Only compares values that are actually present — callers with partial
    data (e.g. an update payload merged with a resource's existing values)
    still get the full set of checks applied to whatever the final,
    merged values would be.
    """
    if pickup_window_start is not None and pickup_window_end is not None:
        if pickup_window_end <= pickup_window_start:
            raise ValueError("pickup_window_end must be after pickup_window_start.")

    if available_time is not None and expiry_time is not None:
        if expiry_time <= available_time:
            raise ValueError("expiry_time must be after available_time.")

    if pickup_window_start is not None and expiry_time is not None:
        if pickup_window_start >= expiry_time:
            raise ValueError("pickup_window_start must be before expiry_time.")

    if pickup_window_end is not None and expiry_time is not None:
        if pickup_window_end > expiry_time:
            raise ValueError("pickup_window_end cannot be after expiry_time.")

    if pickup_window_start is not None and available_time is not None:
        if pickup_window_start < available_time:
            raise ValueError("pickup_window_start cannot be before available_time.")

    # preparation_time (when the food was prepared/cooked) should precede
    # both when it becomes available for pickup and its expiry deadline.
    if preparation_time is not None and available_time is not None:
        if preparation_time > available_time:
            raise ValueError("preparation_time cannot be after available_time.")

    if preparation_time is not None and expiry_time is not None:
        if preparation_time >= expiry_time:
            raise ValueError("preparation_time must be before expiry_time.")


def _validate_food_fields(
    *,
    resource_type: ResourceType,
    food_category: Optional[FoodCategory],
    is_vegetarian: Optional[bool],
    preparation_time: Optional[datetime],
    allergen_info: Optional[list],
    storage_requirements: Optional[StorageRequirement],
    packaging_info: Optional[str],
) -> None:
    """Food-specific fields only make sense on FOOD resources."""
    if resource_type == ResourceType.FOOD:
        return

    values = {
        "food_category": food_category,
        "is_vegetarian": is_vegetarian,
        "preparation_time": preparation_time,
        "allergen_info": allergen_info,
        "storage_requirements": storage_requirements,
        "packaging_info": packaging_info,
    }
    set_fields = [name for name in _FOOD_FIELD_NAMES if values[name] is not None]
    if set_fields:
        raise ValueError(
            f"{', '.join(set_fields)} only apply to FOOD resources, not {resource_type.value}."
        )


def _validate_image_url(value: Optional[str]) -> Optional[str]:
    """`image_url` is expected to be the `url` returned by
    POST /api/uploads/resource-image (or any other absolute URL) — never a
    bare filename/path, which wouldn't be loadable by a client."""
    if value is not None and not (value.startswith("http://") or value.startswith("https://")):
        raise ValueError("image_url must be an absolute http:// or https:// URL.")
    return value


def _validate_allergen_info(allergens: Optional[list]) -> None:
    if not allergens:
        return
    if AllergenType.NONE in allergens and len(allergens) > 1:
        raise ValueError(f"allergen_info cannot combine {AllergenType.NONE.value} with other allergens.")
    if len(set(allergens)) != len(allergens):
        raise ValueError("allergen_info cannot contain duplicate entries.")


class ResourceCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=5000)

    resource_type: ResourceType
    # Free-text subtype, e.g. "vegetarian meals", "antibiotics", "IV fluids".
    category: Optional[str] = Field(default=None, max_length=120)

    quantity: float = Field(gt=0, description="Must be greater than 0.")
    unit: str = Field(default="units", max_length=30)

    urgency: UrgencyLevel = UrgencyLevel.MEDIUM

    available_time: Optional[datetime] = Field(
        default=None, description="When the resource actually becomes ready/available for pickup."
    )
    expiry_time: Optional[datetime] = Field(
        default=None, description="Rescue deadline — after this the resource is no longer usable."
    )
    pickup_window_start: Optional[datetime] = None
    pickup_window_end: Optional[datetime] = None

    location_address: str = Field(min_length=1, max_length=500)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)

    image_url: Optional[str] = Field(default=None, max_length=1000)

    is_perishable: bool = True
    # Optional on input for FOOD; MEDICAL resources are forced to True by
    # the service layer regardless of what's sent here.
    requires_medical_verification: bool = False

    # --- Food-specific fields (FOOD resources only) ---
    food_category: Optional[FoodCategory] = Field(
        default=None, description="Food subtype. Only valid when resource_type is FOOD."
    )
    is_vegetarian: Optional[bool] = Field(default=None, description="Only valid when resource_type is FOOD.")
    preparation_time: Optional[datetime] = Field(
        default=None, description="When the food was prepared/cooked. Only valid when resource_type is FOOD."
    )
    allergen_info: Optional[list[AllergenType]] = Field(
        default=None,
        description="List of allergens present, or [\"NONE\"] if confirmed allergen-free. "
        "Only valid when resource_type is FOOD.",
    )
    storage_requirements: Optional[StorageRequirement] = Field(
        default=None, description="Only valid when resource_type is FOOD."
    )
    packaging_info: Optional[str] = Field(
        default=None, max_length=500, description="Only valid when resource_type is FOOD."
    )

    @field_validator("image_url")
    @classmethod
    def _validate_image_url_create(cls, v: Optional[str]) -> Optional[str]:
        return _validate_image_url(v)

    @model_validator(mode="after")
    def _validate_dates(self) -> "ResourceCreate":
        _check_date_relationships(
            available_time=self.available_time,
            expiry_time=self.expiry_time,
            pickup_window_start=self.pickup_window_start,
            pickup_window_end=self.pickup_window_end,
            preparation_time=self.preparation_time,
        )
        return self

    @model_validator(mode="after")
    def _validate_food(self) -> "ResourceCreate":
        _validate_food_fields(
            resource_type=self.resource_type,
            food_category=self.food_category,
            is_vegetarian=self.is_vegetarian,
            preparation_time=self.preparation_time,
            allergen_info=self.allergen_info,
            storage_requirements=self.storage_requirements,
            packaging_info=self.packaging_info,
        )
        _validate_allergen_info(self.allergen_info)
        return self

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "title": "80 vegetarian meals",
                    "description": "Surplus banquet meals from a cancelled event.",
                    "resource_type": "FOOD",
                    "category": "vegetarian meals",
                    "quantity": 80,
                    "unit": "meals",
                    "urgency": "HIGH",
                    "available_time": "2026-09-17T21:00:00Z",
                    "expiry_time": "2026-09-17T23:59:00Z",
                    "pickup_window_start": "2026-09-17T23:30:00Z",
                    "pickup_window_end": "2026-09-18T01:00:00Z",
                    "location_address": "Grand Plaza Hotel, MG Road, Bengaluru",
                    "latitude": 12.9716,
                    "longitude": 77.5946,
                    "image_url": "https://example.com/images/banquet-meals.jpg",
                    "is_perishable": True,
                    "requires_medical_verification": False,
                    "food_category": "COOKED_MEALS",
                    "is_vegetarian": True,
                    "preparation_time": "2026-09-17T20:00:00Z",
                    "allergen_info": ["MILK", "WHEAT_GLUTEN"],
                    "storage_requirements": "REFRIGERATED",
                    "packaging_info": "Sealed aluminum trays, 10 meals per tray.",
                },
                {
                    "title": "200 units amoxicillin 500mg",
                    "description": "Near-expiry stock, unopened boxes.",
                    "resource_type": "MEDICAL",
                    "category": "antibiotics",
                    "quantity": 200,
                    "unit": "units",
                    "urgency": "MEDIUM",
                    "expiry_time": "2026-10-01T00:00:00Z",
                    "location_address": "City Pharmacy, 4th Block, Bengaluru",
                    "is_perishable": True,
                },
            ]
        }
    )


class ResourceUpdate(BaseModel):
    """
    All fields optional — only the ones provided are changed. `status` may
    only be moved to AVAILABLE or CANCELLED here; every other transition
    (MATCHING, ALLOCATED, IN_TRANSIT, DELIVERED, EXPIRED) is driven by the
    matching/operations engine in later stages, not by a direct client edit.
    """

    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=5000)
    category: Optional[str] = Field(default=None, max_length=120)

    quantity: Optional[float] = Field(default=None, gt=0)
    unit: Optional[str] = Field(default=None, max_length=30)

    status: Optional[ResourceStatus] = None
    urgency: Optional[UrgencyLevel] = None

    available_time: Optional[datetime] = None
    expiry_time: Optional[datetime] = None
    pickup_window_start: Optional[datetime] = None
    pickup_window_end: Optional[datetime] = None

    location_address: Optional[str] = Field(default=None, min_length=1, max_length=500)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)

    image_url: Optional[str] = Field(default=None, max_length=1000)

    is_perishable: Optional[bool] = None
    requires_medical_verification: Optional[bool] = None

    # --- Food-specific fields (FOOD resources only) ---
    # resource_type itself can't be changed via update (see class docstring
    # context above — it's create-time only), so type-appropriateness of
    # these can only be fully checked once merged with the resource's
    # existing resource_type — the service layer does that after merging,
    # the same way it re-checks dates below.
    food_category: Optional[FoodCategory] = None
    is_vegetarian: Optional[bool] = None
    preparation_time: Optional[datetime] = None
    allergen_info: Optional[list[AllergenType]] = None
    storage_requirements: Optional[StorageRequirement] = None
    packaging_info: Optional[str] = Field(default=None, max_length=500)

    @field_validator("image_url")
    @classmethod
    def _validate_image_url_update(cls, v: Optional[str]) -> Optional[str]:
        return _validate_image_url(v)

    @field_validator("status")
    @classmethod
    def _validate_status_transition(cls, v: Optional[ResourceStatus]) -> Optional[ResourceStatus]:
        allowed = {ResourceStatus.AVAILABLE, ResourceStatus.CANCELLED}
        if v is not None and v not in allowed:
            raise ValueError(
                f"status can only be set to {', '.join(s.value for s in allowed)} directly. "
                "Other statuses are set automatically by the matching/operations engine."
            )
        return v

    @model_validator(mode="after")
    def _validate_dates(self) -> "ResourceUpdate":
        # This only catches inconsistencies among fields present in *this*
        # payload. Because an update can be partial, the service layer runs
        # the same check again after merging with the resource's existing
        # values, to catch e.g. a lone new pickup_window_start that now
        # conflicts with an untouched expiry_time.
        _check_date_relationships(
            available_time=self.available_time,
            expiry_time=self.expiry_time,
            pickup_window_start=self.pickup_window_start,
            pickup_window_end=self.pickup_window_end,
            preparation_time=self.preparation_time,
        )
        return self

    @model_validator(mode="after")
    def _validate_food(self) -> "ResourceUpdate":
        # Only the shape of allergen_info can be checked here (no
        # dependency on the resource's existing type); the FOOD-only
        # type-appropriateness check happens in the service layer once
        # merged with the resource's actual resource_type.
        _validate_allergen_info(self.allergen_info)
        return self


class ProviderSummary(BaseModel):
    """Minimal provider info embedded in a resource response."""

    id: uuid.UUID
    full_name: str
    phone: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ResourceOut(BaseModel):
    id: uuid.UUID
    provider_id: uuid.UUID
    provider: Optional[ProviderSummary] = None

    title: str
    description: Optional[str] = None

    resource_type: ResourceType
    category: Optional[str] = None

    quantity: float
    unit: str

    status: ResourceStatus
    urgency: UrgencyLevel

    available_time: Optional[datetime] = None
    expiry_time: Optional[datetime] = None
    pickup_window_start: Optional[datetime] = None
    pickup_window_end: Optional[datetime] = None

    location_address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    image_url: Optional[str] = None

    is_perishable: bool
    requires_medical_verification: bool
    ai_analysis: Optional[ResourceAnalysisResult] = Field(
        default=None, description="Most recent Gemini structured analysis, if this resource has been analyzed."
    )

    food_category: Optional[FoodCategory] = None
    is_vegetarian: Optional[bool] = None
    preparation_time: Optional[datetime] = None
    allergen_info: Optional[list[AllergenType]] = None
    storage_requirements: Optional[StorageRequirement] = None
    packaging_info: Optional[str] = None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ResourceListData(BaseModel):
    items: list[ResourceOut]
    total: int
    skip: int
    limit: int
