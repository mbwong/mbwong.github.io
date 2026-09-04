"""Coding schema for the ticketing-discontent pilot.

The pydantic models here are the single source of truth: they drive the
structured-output contract sent to the model, validate human-coded records, and
define the columns the exhibits are built from. Changing a field means bumping
CODEBOOK_VERSION.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

CODEBOOK_VERSION = "0.1"


class Stage(str, Enum):
    ALLOCATION = "S1_ALLOCATION"
    SALE = "S2_SALE"
    SECONDARY = "S3_SECONDARY"
    POSTPURCHASE = "S4_POSTPURCHASE"
    EVENTDAY = "S5_EVENTDAY"
    DIFFUSE = "S0_DIFFUSE"


class Attribution(str, Enum):
    GOVERNMENT = "GOVERNMENT"
    PLATFORM = "PLATFORM"
    PROMOTER = "PROMOTER"
    SCALPER = "SCALPER"
    OTHER_FANS = "OTHER_FANS"
    NONE = "NONE"


class Affect(str, Enum):
    GRIEVANCE = "GRIEVANCE"
    RESIGNATION = "RESIGNATION"
    MOBILISATION = "MOBILISATION"
    DEFENCE = "DEFENCE"


class Coding(BaseModel):
    """One coded unit. Mirrors codebook.md sections 2-3."""

    in_scope: bool = Field(
        description="False if the unit fails the codebook section 1 exclusion "
        "rules (not HK live-event ticketing, pure advertisement, "
        "non-substantive). When False, every other field is ignored."
    )
    stage: Stage = Field(description="Primary pipeline stage of the grievance.")
    secondary_stages: List[Stage] = Field(
        default_factory=list,
        description="Other stages present in the same unit. May be empty.",
    )
    attribution: Attribution = Field(
        description="Who the author explicitly blames. NONE unless explicit."
    )
    affect: Affect = Field(description="Stance, not sentiment polarity.")
    remedy_named: bool = Field(
        description="True if the author names a concrete policy or operational fix."
    )
    first_person: bool = Field(
        description="True if the author claims direct personal experience."
    )
    event_ref: Optional[str] = Field(
        default=None, description="Event, artist, or venue named, else null."
    )
    money_claim_hkd: Optional[float] = Field(
        default=None,
        description="A specific HKD amount the author states (price, markup, or "
        "loss). Null if no figure is given. Convert 'HK$1,399' to 1399.",
    )
    rationale: str = Field(
        description="One sentence, in English, quoting the phrase that decided "
        "the stage. Used for audit, not for analysis."
    )


class CodedUnit(BaseModel):
    """A coded record joined back to its source unit."""

    unit_id: str
    source: str
    coder: str  # "human:ABC", "model:claude-opus-5", "gold"
    codebook_version: str = CODEBOOK_VERSION
    coding: Coding


# Fields that reliability is computed on, and the minimum kappa required
# before the pipeline may proceed (codebook.md section 5).
RELIABILITY_THRESHOLDS = {
    "stage": 0.70,
    "attribution": 0.60,
    "affect": 0.60,
}


def coding_json_schema() -> dict:
    """JSON schema for the structured-output contract.

    Anthropic structured outputs require additionalProperties: false and an
    explicit required list on every object, which pydantic does not emit by
    default for optional fields.
    """
    schema = Coding.model_json_schema()
    schema["additionalProperties"] = False
    schema["required"] = list(schema["properties"].keys())
    for definition in schema.get("$defs", {}).values():
        if definition.get("type") == "object":
            definition["additionalProperties"] = False
    return schema
