"""Pipeline state models for claim lifecycle tracking."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ScrubIssue(BaseModel):
    severity: str  # "reject" | "warn" | "info"
    code: str
    message: str
    suggestion: str = ""


class ScrubResult(BaseModel):
    status: str  # "pass" | "warn" | "reject"
    issues: list[ScrubIssue] = Field(default_factory=list)
    payer_rules_checked: int = 0
    confidence: float = 1.0


class CPTCode(BaseModel):
    code: str
    description: str = ""
    modifier: str = ""
    confidence: float = 1.0
    charge: float = 0.0


class ICD10Code(BaseModel):
    code: str
    description: str = ""
    confidence: float = 1.0


class ChargeCaptureResult(BaseModel):
    encounter_id: str
    cpt_codes: list[CPTCode] = Field(default_factory=list)
    icd10_codes: list[ICD10Code] = Field(default_factory=list)
    place_of_service: str = "11"
    total_estimated_charge: float = 0.0


class ClaimPipelineItem(BaseModel):
    id: str
    patient_id: str
    patient_name: str = ""
    encounter_id: str
    status: str = "captured"  # captured | scrubbed | submitted | pending | paid | denied | appealed | resolved
    cpt_codes: list[str] = Field(default_factory=list)
    icd10_codes: list[str] = Field(default_factory=list)
    total_charge: float = 0.0
    payer: str = ""
    payer_name: str = ""
    provider: str = ""
    facility: str = ""
    date_of_service: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    scrub_result: Optional[ScrubResult] = None
    denial_code: Optional[str] = None
    denial_reason: Optional[str] = None
    appeal_id: Optional[str] = None
    appeal_text: Optional[str] = None
    paid_amount: Optional[float] = None
    era_id: Optional[str] = None


class PipelineStats(BaseModel):
    total_claims: int = 0
    by_status: dict[str, int] = Field(default_factory=dict)
    total_charges: float = 0.0
    total_paid: float = 0.0
    total_denied: float = 0.0
    denial_rate: float = 0.0
    average_charge: float = 0.0
    top_denial_codes: list[dict] = Field(default_factory=list)
