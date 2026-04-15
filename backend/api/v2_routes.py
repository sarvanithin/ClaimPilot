"""V2 API routes for full RCM pipeline — extends v1 without modifying existing routes."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.agents.eligibility import EligibilityAgent
from backend.agents.charge_capture import ChargeCaptureAgent
from backend.agents.claim_scrubber import ClaimScrubber
from backend.agents.claim_submitter import ClaimSubmitter, get_pipeline, get_pipeline_item
from backend.agents.denial_manager import DenialManager, CARC_DESCRIPTIONS
from backend.fhir.seed_data import (
    get_all_patients,
    get_patient,
    get_patient_encounters,
    get_encounter,
    get_patient_coverage,
)
from backend.models.pipeline import PipelineStats

v2_router = APIRouter(prefix="/api/v2", tags=["V2 RCM"])

# Agent instances
_eligibility_agent = EligibilityAgent()
_charge_agent = ChargeCaptureAgent()
_scrubber = ClaimScrubber()
_submitter = ClaimSubmitter()
_denial_manager = DenialManager()


# ─── Request/Response models ───────────────────────────────────────

class ChargeCaptureRequest(BaseModel):
    encounter_id: str
    clinical_note: Optional[str] = None
    encounter_type: str = ""


class ScrubRequest(BaseModel):
    cpt_codes: list[str]
    icd10_codes: list[str]
    payer: str
    modifiers: dict[str, str] = Field(default_factory=dict)
    date_of_service: str = ""
    has_prior_auth: bool = False


class SubmitRequest(BaseModel):
    encounter_id: str
    patient_id: str


class DenyRequest(BaseModel):
    carc_code: str = "CO-50"


class AppealRequest(BaseModel):
    pass  # No additional data needed beyond the claim_id in the path


class EligibilityRequest(BaseModel):
    patient_id: str
    date_of_service: str = ""


# ─── FHIR Patient Endpoints ────────────────────────────────────────

@v2_router.get("/fhir/patients")
async def list_patients():
    """List all FHIR patients with summary info."""
    patients = get_all_patients()
    results = []
    for p in patients:
        coverage = get_patient_coverage(p.id)
        encounters = get_patient_encounters(p.id)
        results.append({
            "id": p.id,
            "name": p.name[0].full_name if p.name else "",
            "gender": p.gender,
            "birthDate": p.birthDate,
            "conditions": p.conditions,
            "payer": coverage.payer_name if coverage else "Unknown",
            "plan": coverage.plan if coverage else "",
            "member_id": coverage.member_id if coverage else "",
            "encounter_count": len(encounters),
        })
    return {"patients": results, "total": len(results)}


@v2_router.get("/fhir/patients/{patient_id}")
async def get_patient_detail(patient_id: str):
    """Get detailed FHIR patient information."""
    patient = get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    coverage = get_patient_coverage(patient_id)
    encounters = get_patient_encounters(patient_id)
    return {
        "patient": patient.model_dump(),
        "coverage": coverage.model_dump() if coverage else None,
        "encounters": [e.model_dump(by_alias=True) for e in encounters],
    }


@v2_router.get("/fhir/patients/{patient_id}/encounters")
async def get_patient_encounters_route(patient_id: str):
    """Get all encounters for a patient."""
    patient = get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    encounters = get_patient_encounters(patient_id)
    return {
        "patient_id": patient_id,
        "patient_name": patient.name[0].full_name if patient.name else "",
        "encounters": [
            {
                "id": e.id,
                "date": e.date,
                "type": e.type,
                "provider": e.provider,
                "facility": e.facility,
                "status": e.status,
                "clinical_note": e.clinical_note,
            }
            for e in encounters
        ],
        "total": len(encounters),
    }


# ─── Eligibility ───────────────────────────────────────────────────

@v2_router.post("/eligibility/verify")
async def verify_eligibility(request: EligibilityRequest):
    """Verify patient insurance eligibility."""
    result = await _eligibility_agent.verify(request.patient_id, request.date_of_service)
    return result.model_dump()


# ─── Charge Capture ────────────────────────────────────────────────

@v2_router.post("/charges/capture")
async def capture_charges(request: ChargeCaptureRequest):
    """Capture charges from an encounter's clinical note."""
    encounter = get_encounter(request.encounter_id)
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")

    clinical_note = request.clinical_note or encounter.clinical_note
    result = await _charge_agent.capture(
        encounter_id=request.encounter_id,
        clinical_note=clinical_note,
        encounter_type=encounter.type,
    )
    return result.model_dump()


# ─── Claim Scrubbing ──────────────────────────────────────────────

@v2_router.post("/claims/scrub")
async def scrub_claim(request: ScrubRequest):
    """Scrub/validate a claim before submission."""
    result = await _scrubber.scrub(
        cpt_codes=request.cpt_codes,
        icd10_codes=request.icd10_codes,
        payer=request.payer,
        modifiers=request.modifiers,
        date_of_service=request.date_of_service,
        has_prior_auth=request.has_prior_auth,
    )
    return result.model_dump()


# ─── Claim Submission ─────────────────────────────────────────────

@v2_router.post("/claims/submit")
async def submit_claim(request: SubmitRequest):
    """Run full pipeline: capture charges, scrub, generate 837P, and submit."""
    encounter = get_encounter(request.encounter_id)
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")

    patient = get_patient(request.patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    coverage = get_patient_coverage(request.patient_id)
    payer = coverage.payer if coverage else "UHC"

    # Step 1: Charge capture
    charge_result = await _charge_agent.capture(
        encounter_id=request.encounter_id,
        clinical_note=encounter.clinical_note,
        encounter_type=encounter.type,
    )

    # Step 2: Scrub
    modifiers = {c.code: c.modifier for c in charge_result.cpt_codes if c.modifier}
    scrub_result = await _scrubber.scrub(
        cpt_codes=[c.code for c in charge_result.cpt_codes],
        icd10_codes=[c.code for c in charge_result.icd10_codes],
        payer=payer,
        modifiers=modifiers,
        date_of_service=encounter.date,
    )

    # Step 3: Generate 837P
    claim_837p = await _submitter.generate_837p(charge_result, request.patient_id)

    # Step 4: Submit to pipeline
    pipeline_item = await _submitter.submit_to_pipeline(
        claim_837p, request.encounter_id, scrub_result
    )

    return {
        "claim_id": pipeline_item.id,
        "status": pipeline_item.status,
        "charge_capture": charge_result.model_dump(),
        "scrub_result": scrub_result.model_dump(),
        "claim_837p": claim_837p.to_x12_summary(),
        "pipeline_item": pipeline_item.model_dump(),
    }


# ─── Denial & Appeal ──────────────────────────────────────────────

@v2_router.post("/claims/{claim_id}/deny")
async def deny_claim(claim_id: str, request: DenyRequest):
    """Simulate a claim denial (for demo purposes)."""
    result = await _denial_manager.simulate_denial(claim_id, request.carc_code)
    if not result:
        raise HTTPException(status_code=404, detail="Claim not found in pipeline")
    return result.model_dump()


@v2_router.post("/claims/{claim_id}/appeal")
async def appeal_claim(claim_id: str):
    """Generate an appeal for a denied claim."""
    denial = await _denial_manager.simulate_denial(claim_id)
    if not denial:
        # Try to create denial details from pipeline item
        item = get_pipeline_item(claim_id)
        if not item:
            raise HTTPException(status_code=404, detail="Claim not found in pipeline")
        if item.status != "denied":
            raise HTTPException(status_code=400, detail="Claim is not in denied status")

    result = await _denial_manager.generate_appeal(denial)
    return result.model_dump()


# ─── Pipeline ─────────────────────────────────────────────────────

@v2_router.get("/pipeline")
async def get_full_pipeline():
    """Get the full claim pipeline state."""
    pipeline = get_pipeline()
    items = [item.model_dump() for item in pipeline.values()]
    # Sort by updated_at descending
    items.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return {"items": items, "total": len(items)}


@v2_router.get("/pipeline/stats")
async def get_pipeline_stats():
    """Get pipeline statistics."""
    pipeline = get_pipeline()
    items = list(pipeline.values())

    if not items:
        return PipelineStats().model_dump()

    by_status: dict[str, int] = {}
    total_charges = 0.0
    total_paid = 0.0
    total_denied = 0.0
    denial_codes: dict[str, int] = {}

    for item in items:
        by_status[item.status] = by_status.get(item.status, 0) + 1
        total_charges += item.total_charge
        if item.paid_amount:
            total_paid += item.paid_amount
        if item.status == "denied":
            total_denied += item.total_charge
            if item.denial_code:
                denial_codes[item.denial_code] = denial_codes.get(item.denial_code, 0) + 1

    top_denial_codes = sorted(
        [{"code": k, "count": v, "description": CARC_DESCRIPTIONS.get(k, "")} for k, v in denial_codes.items()],
        key=lambda x: x["count"],
        reverse=True,
    )[:5]

    denial_count = by_status.get("denied", 0) + by_status.get("appealed", 0)
    denial_rate = denial_count / len(items) if items else 0.0

    return PipelineStats(
        total_claims=len(items),
        by_status=by_status,
        total_charges=total_charges,
        total_paid=total_paid,
        total_denied=total_denied,
        denial_rate=denial_rate,
        average_charge=total_charges / len(items) if items else 0.0,
        top_denial_codes=top_denial_codes,
    ).model_dump()


@v2_router.get("/pipeline/{claim_id}")
async def get_pipeline_claim(claim_id: str):
    """Get a specific claim from the pipeline."""
    item = get_pipeline_item(claim_id)
    if not item:
        raise HTTPException(status_code=404, detail="Claim not found in pipeline")
    return item.model_dump()


@v2_router.get("/denial-codes")
async def list_denial_codes():
    """List all known CARC denial codes."""
    return [
        {"code": code, "description": desc}
        for code, desc in CARC_DESCRIPTIONS.items()
    ]
