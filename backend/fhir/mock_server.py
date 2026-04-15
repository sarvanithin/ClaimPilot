"""Mock FHIR R4 server endpoints mounted as a FastAPI sub-router."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.fhir.seed_data import (
    get_all_patients,
    get_patient,
    get_all_encounters,
    get_encounter,
    get_patient_encounters,
    get_all_coverages,
    get_coverage,
    get_patient_coverage,
)
from backend.models.fhir_types import FHIRBundle

fhir_router = APIRouter(prefix="/fhir", tags=["FHIR"])


def _bundle(entries: list[dict], total: int | None = None) -> dict:
    """Wrap results in a FHIR Bundle."""
    return FHIRBundle(
        type="searchset",
        total=total if total is not None else len(entries),
        entry=[{"resource": e} for e in entries],
    ).model_dump()


@fhir_router.get("/Patient")
async def list_patients():
    patients = get_all_patients()
    return _bundle([p.model_dump() for p in patients])


@fhir_router.get("/Patient/{patient_id}")
async def read_patient(patient_id: str):
    patient = get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")
    return patient.model_dump()


@fhir_router.get("/Patient/{patient_id}/Encounter")
async def patient_encounters(patient_id: str):
    patient = get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")
    encounters = get_patient_encounters(patient_id)
    return _bundle([e.model_dump(by_alias=True) for e in encounters])


@fhir_router.get("/Encounter/{encounter_id}")
async def read_encounter(encounter_id: str):
    encounter = get_encounter(encounter_id)
    if not encounter:
        raise HTTPException(status_code=404, detail=f"Encounter {encounter_id} not found")
    return encounter.model_dump(by_alias=True)


@fhir_router.get("/Coverage")
async def list_coverages():
    coverages = get_all_coverages()
    return _bundle([c.model_dump() for c in coverages])


@fhir_router.get("/Coverage/{coverage_id}")
async def read_coverage(coverage_id: str):
    coverage = get_coverage(coverage_id)
    if not coverage:
        raise HTTPException(status_code=404, detail=f"Coverage {coverage_id} not found")
    return coverage.model_dump()


@fhir_router.get("/Patient/{patient_id}/Coverage")
async def patient_coverage(patient_id: str):
    coverage = get_patient_coverage(patient_id)
    if not coverage:
        raise HTTPException(status_code=404, detail=f"No coverage found for patient {patient_id}")
    return coverage.model_dump()


# In-memory claim store for submitted claims
_claims_store: dict[str, dict] = {}


@fhir_router.post("/Claim")
async def create_claim(claim: dict):
    """Accept a FHIR Claim resource and store it."""
    claim_id = claim.get("id", f"claim-{len(_claims_store) + 1:04d}")
    claim["id"] = claim_id
    claim["resourceType"] = "Claim"
    _claims_store[claim_id] = claim
    return claim


@fhir_router.get("/Claim/{claim_id}")
async def read_claim(claim_id: str):
    claim = _claims_store.get(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")
    return claim


@fhir_router.get("/Claim")
async def list_claims():
    claims = list(_claims_store.values())
    return _bundle(claims)
