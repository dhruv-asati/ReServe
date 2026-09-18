"""
Gemini AI service: turns a Resource's freeform fields into the strict,
structured `ResourceAnalysis` schema (see app/schemas/analysis.py), so
downstream consumers — a provider's dashboard, a future matching engine —
get consistent fields regardless of how the original title/description
was written.

Hard boundary this module enforces: Gemini only ANALYZES AND STRUCTURES
information here. It never decides whether a resource gets allocated,
matched, or accepted — nothing in this module (or the resource_service
function that calls it) ever changes `Resource.status` or creates a
RescueRequest/Match/Allocation. The output is advisory metadata stored in
`Resource.ai_analysis`, for a human or a later matching engine to use.
This is enforced three ways: the system instruction below explicitly
tells the model not to make that decision, the response schema has no
field that could represent one, and the calling code only ever writes to
`ai_analysis`.

Split into two functions specifically so tests never need a real
GEMINI_API_KEY or network access:

    call_gemini_model(prompt) -> str        # the ONLY function that talks to Google
    analyze_resource(resource) -> ResourceAnalysisResult   # builds the prompt, calls the
                                                            # above, validates the result

A test monkeypatches `gemini_service.call_gemini_model` (and
`gemini_service.is_configured`, to skip the "not configured" guard)
to return a canned JSON string — prompt-building, response parsing,
Pydantic validation, and error handling all still run for real. See
tests/test_resource_analysis.py.
"""

import json
import logging
from datetime import datetime, timezone
from functools import lru_cache

from app.core.config import get_settings
from app.core.errors import AppError
from app.models.resource import Resource
from app.schemas.analysis import ResourceAnalysis, ResourceAnalysisResult

logger = logging.getLogger(__name__)

_SYSTEM_INSTRUCTION = (
    "You are a structuring assistant for a surplus-resource rescue platform. Your ONLY job is "
    "to read the details of a donated food or medical resource and organize that information "
    "into the given JSON schema. "
    "You must NEVER decide whether the resource should be allocated, matched, accepted, or "
    "rejected, and you must NEVER recommend a specific recipient, partner, or hub — those "
    "decisions belong to a separate system and to human reviewers. Only describe and classify "
    "the resource itself. "
    "Respond with ONLY a single JSON object matching the given schema — no prose, no markdown "
    "code fences, no extra commentary."
)


def is_configured() -> bool:
    return bool(get_settings().GEMINI_API_KEY)


@lru_cache
def _get_model():
    # Imported lazily so an environment that never sets GEMINI_API_KEY
    # doesn't need a working `google-generativeai` install just to boot.
    import google.generativeai as genai

    settings = get_settings()
    genai.configure(api_key=settings.GEMINI_API_KEY)
    return genai.GenerativeModel(settings.GEMINI_MODEL, system_instruction=_SYSTEM_INSTRUCTION)


def _resource_facts(resource: Resource) -> dict:
    """Everything about the resource that's useful context for analysis,
    from both the common and food-specific field groups. Values are kept
    JSON-serializable (enums/dates -> str) since this is embedded
    directly into the prompt text."""
    return {
        "resource_type": resource.resource_type.value,
        "title": resource.title,
        "description": resource.description,
        "category": resource.category,
        "quantity": float(resource.quantity),
        "unit": resource.unit,
        "urgency_as_posted": resource.urgency.value,
        "available_time": resource.available_time.isoformat() if resource.available_time else None,
        "expiry_time": resource.expiry_time.isoformat() if resource.expiry_time else None,
        "pickup_window_start": resource.pickup_window_start.isoformat() if resource.pickup_window_start else None,
        "pickup_window_end": resource.pickup_window_end.isoformat() if resource.pickup_window_end else None,
        "location_address": resource.location_address,
        "is_perishable": resource.is_perishable,
        "requires_medical_verification": resource.requires_medical_verification,
        # Food-specific — null/absent for MEDICAL resources.
        "food_category": resource.food_category.value if resource.food_category else None,
        "is_vegetarian": resource.is_vegetarian,
        "preparation_time": resource.preparation_time.isoformat() if resource.preparation_time else None,
        "allergen_info": resource.allergen_info,
        "storage_requirements_as_posted": (
            resource.storage_requirements.value if resource.storage_requirements else None
        ),
        "packaging_info": resource.packaging_info,
    }


def _build_prompt(resource: Resource) -> str:
    schema = ResourceAnalysis.model_json_schema()
    return (
        "Resource details (JSON):\n"
        f"{json.dumps(_resource_facts(resource), default=str)}\n\n"
        "Return a single JSON object that matches exactly this JSON schema "
        "(fill in every field; use null only where the schema allows it):\n"
        f"{json.dumps(schema)}"
    )


def call_gemini_model(prompt: str) -> str:
    """
    The only function in this module that actually talks to Google. Kept
    as a thin, separately-mockable seam — tests monkeypatch this function
    directly instead of exercising the real SDK/network call.
    """
    settings = get_settings()
    model = _get_model()
    response = model.generate_content(
        prompt,
        generation_config={"response_mime_type": "application/json"},
        request_options={"timeout": settings.GEMINI_TIMEOUT_SECONDS},
    )
    return response.text


def _strip_markdown_fences(text: str) -> str:
    """Defensive cleanup — JSON mode should prevent this, but some model
    responses still wrap output in ```json ... ``` fences."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    return cleaned.strip()


def analyze_resource(resource: Resource) -> ResourceAnalysisResult:
    """
    Builds a prompt from `resource`, calls Gemini, and validates the
    response against the strict ResourceAnalysis schema. Raises AppError
    on any failure — this never returns (or lets a caller store) a
    partially-valid result.
    """
    if not is_configured():
        raise AppError(
            status_code=503,
            code="AI_ANALYSIS_NOT_CONFIGURED",
            message="AI analysis is not available: GEMINI_API_KEY is not configured on the server.",
        )

    prompt = _build_prompt(resource)

    try:
        raw_text = call_gemini_model(prompt)
    except Exception as exc:
        # Log only the exception's type, never str(exc) or the prompt —
        # some Gemini SDK/transport errors embed the request URL, which
        # for this SDK includes the API key as a query parameter.
        exc_name = type(exc).__name__
        if "timeout" in exc_name.lower() or "deadline" in exc_name.lower():
            logger.warning("Gemini analysis timed out for resource %s", resource.id)
            raise AppError(
                status_code=504,
                code="AI_ANALYSIS_TIMEOUT",
                message="AI analysis timed out. Please try again.",
            )
        logger.error("Gemini analysis failed for resource %s (%s)", resource.id, exc_name)
        raise AppError(
            status_code=502,
            code="AI_ANALYSIS_FAILED",
            message="AI analysis service is temporarily unavailable. Please try again later.",
        )

    try:
        payload = json.loads(_strip_markdown_fences(raw_text))
        analysis = ResourceAnalysis.model_validate(payload)
    except Exception:
        # Also never log raw_text itself here in production-grade code —
        # it's model output about the resource, not a secret, but we keep
        # this log line free of it anyway to avoid unbounded log growth
        # from a verbose/malformed response.
        logger.error("Gemini returned an unparseable/invalid response for resource %s", resource.id)
        raise AppError(
            status_code=502,
            code="AI_ANALYSIS_INVALID_RESPONSE",
            message="AI analysis returned an unexpected response format. Please try again.",
        )

    settings = get_settings()
    return ResourceAnalysisResult(
        analysis=analysis,
        model=settings.GEMINI_MODEL,
        analyzed_at=datetime.now(timezone.utc),
    )
