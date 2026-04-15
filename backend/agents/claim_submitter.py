"""Claim Submitter Agent — generates 837P claims and manages pipeline submission."""

from __future__ import annotations

import uuid
from datetime import datetime

from backend.fhir.seed_data import get_patient, get_patient_coverage, get_encounter
from backend.models.pipeline import ClaimPipelineItem, ChargeCaptureResult
from backend.models.x12 import Claim837P, ServiceLine
from backend.rules.cpt_icd_map import get_cpt_charge


# In-memory pipeline store
_pipeline: dict[str, ClaimPipelineItem] = {}


def get_pipeline() -> dict[str, ClaimPipelineItem]:
    return _pipeline


def get_pipeline_item(claim_id: str) -> ClaimPipelineItem | None:
    return _pipeline.get(claim_id)


class ClaimSubmitter:
    """Generates 837P claims from charge capture results and submits to pipeline."""

    async def generate_837p(
        self,
        charge_result: ChargeCaptureResult,
        patient_id: str,
    ) -> Claim837P:
        """Generate an 837P claim from charge capture output."""
        patient = get_patient(patient_id)
        coverage = get_patient_coverage(patient_id)
        encounter = get_encounter(charge_result.encounter_id)

        patient_name = ""
        patient_dob = ""
        patient_gender = ""
        if patient and patient.name:
            patient_name = patient.name[0].full_name
            patient_dob = patient.birthDate
            patient_gender = patient.gender

        payer_id = ""
        payer_name = ""
        subscriber_id = ""
        if coverage:
            payer_id = coverage.payer
            payer_name = coverage.payer_name
            subscriber_id = coverage.member_id

        provider_name = ""
        facility_name = ""
        date_of_service = ""
        if encounter:
            provider_name = encounter.provider
            facility_name = encounter.facility
            date_of_service = encounter.date

        claim_id = f"CLM-{uuid.uuid4().hex[:8].upper()}"

        service_lines = []
        for i, cpt in enumerate(charge_result.cpt_codes, 1):
            service_lines.append(ServiceLine(
                line_number=i,
                cpt_code=cpt.code,
                modifier=cpt.modifier,
                icd10_pointers=list(range(1, min(len(charge_result.icd10_codes) + 1, 5))),
                units=1,
                charge_amount=cpt.charge,
                place_of_service=charge_result.place_of_service,
                date_of_service=date_of_service,
            ))

        return Claim837P(
            claim_id=claim_id,
            patient_id=patient_id,
            patient_name=patient_name,
            patient_dob=patient_dob,
            patient_gender=patient_gender,
            subscriber_id=subscriber_id,
            payer_id=payer_id,
            payer_name=payer_name,
            provider_name=provider_name,
            facility_name=facility_name,
            diagnosis_codes=[icd.code for icd in charge_result.icd10_codes],
            service_lines=service_lines,
            total_charge=charge_result.total_estimated_charge,
            place_of_service=charge_result.place_of_service,
        )

    async def submit_to_pipeline(
        self,
        claim_837p: Claim837P,
        encounter_id: str,
        scrub_result=None,
    ) -> ClaimPipelineItem:
        """Submit a claim to the processing pipeline."""
        item = ClaimPipelineItem(
            id=claim_837p.claim_id,
            patient_id=claim_837p.patient_id,
            patient_name=claim_837p.patient_name,
            encounter_id=encounter_id,
            status="submitted",
            cpt_codes=[sl.cpt_code for sl in claim_837p.service_lines],
            icd10_codes=claim_837p.diagnosis_codes,
            total_charge=claim_837p.total_charge,
            payer=claim_837p.payer_id,
            payer_name=claim_837p.payer_name,
            provider=claim_837p.provider_name,
            facility=claim_837p.facility_name,
            date_of_service=claim_837p.service_lines[0].date_of_service if claim_837p.service_lines else "",
            scrub_result=scrub_result,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        _pipeline[item.id] = item
        return item

    async def update_status(self, claim_id: str, status: str, **kwargs) -> ClaimPipelineItem | None:
        """Update pipeline item status."""
        item = _pipeline.get(claim_id)
        if not item:
            return None
        item.status = status
        item.updated_at = datetime.utcnow()
        for key, value in kwargs.items():
            if hasattr(item, key):
                setattr(item, key, value)
        return item
