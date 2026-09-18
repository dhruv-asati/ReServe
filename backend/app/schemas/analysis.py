"""
Pydantic schemas for POST /api/resources/{resource_id}/analyze.

`ResourceAnalysis` is the strict schema Gemini's output is validated
against — a deliberately narrow, fixed field set (enums, bounded floats,
length-capped strings/lists) so a malformed or hallucinated response
fails validation instead of being stored as-is (see
app/services/gemini_service.py, which raises AI_ANALYSIS_INVALID_RESPONSE
whenever this validation fails).

Boundary this schema enforces: every field here *describes or classifies*
the resource. None of them represent, or could be mistaken for, an
allocation/matching decision (no "recommended recipient", no
"accept/reject", no status). That decision is made elsewhere — by a
human, or by a later matching engine — never by this endpoint or by
Gemini itself.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import UrgencyLevel


class ExtractedQuantity(BaseModel):
    """
    Gemini's best-effort read of the actual quantity available, parsed
    from the resource's free-text title/description — distinct from (and
    a cross-check against) the provider's own structured `quantity`/
    `unit` fields, useful when the text describes something that looks
    inconsistent with what was entered in those fields.
    """

    value: Optional[float] = Field(default=None, ge=0)
    unit: Optional[str] = Field(default=None, max_length=30)
    matches_posted_quantity: bool = Field(
        description="True if this roughly matches the resource's own posted quantity/unit."
    )


class RescueWindow(BaseModel):
    """
    Gemini's own assessment of how urgently this resource needs to be
    picked up, independent of (and a cross-check against) the provider's
    own rescue deadline / pickup window fields.
    """

    recommended_pickup_within_hours: Optional[float] = Field(default=None, ge=0)
    reasoning: str = Field(max_length=500)


class ResourceAnalysis(BaseModel):
    """The exact structured output Gemini must return for one resource."""

    resource_category: str = Field(
        max_length=120,
        description="Broad classification, e.g. 'Perishable food', 'Prescription medication'.",
    )
    resource_subtype: str = Field(
        max_length=120, description="Narrower classification, e.g. 'Cooked meals', 'Antibiotic'."
    )
    extracted_quantity: ExtractedQuantity
    urgency_level: UrgencyLevel = Field(description="Gemini's own urgency assessment.")
    rescue_window: RescueWindow
    important_attributes: list[str] = Field(
        default_factory=list,
        max_length=20,
        description="Notable properties, e.g. 'contains dairy', 'requires refrigeration', 'unopened packaging'.",
    )
    storage_requirements: str = Field(max_length=300)
    eligibility_info: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Who this is suited/restricted to, if anything — null if nothing applies.",
    )
    warnings: list[str] = Field(
        default_factory=list,
        max_length=20,
        description="Safety/handling concerns a rescuer or recipient should know about.",
    )
    confidence_score: float = Field(ge=0, le=1)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "resource_category": "Perishable food",
                "resource_subtype": "Cooked meals",
                "extracted_quantity": {"value": 80, "unit": "meals", "matches_posted_quantity": True},
                "urgency_level": "HIGH",
                "rescue_window": {
                    "recommended_pickup_within_hours": 3,
                    "reasoning": "Cooked food held at room temperature degrades quickly.",
                },
                "important_attributes": ["contains dairy", "individually packaged"],
                "storage_requirements": "Keep refrigerated below 4C until pickup.",
                "eligibility_info": None,
                "warnings": ["Contains milk and wheat allergens."],
                "confidence_score": 0.86,
            }
        }
    )


class ResourceAnalysisResult(BaseModel):
    """
    What's actually stored in `Resource.ai_analysis` and returned in
    `ResourceOut.ai_analysis`. Wraps `ResourceAnalysis` with the metadata
    needed to know which model produced it and when, so a stale analysis
    from before an edit (or a previous Gemini model version) is visibly
    distinguishable from a fresh one — re-running the analyze endpoint
    always overwrites this with a new result.
    """

    analysis: ResourceAnalysis
    model: str
    analyzed_at: datetime

    model_config = ConfigDict(from_attributes=True)
