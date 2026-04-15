"""Denial Manager Agent — parses 835 ERA denials and orchestrates appeals."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from backend.agents.claim_submitter import get_pipeline_item, get_pipeline
from backend.fhir.seed_data import get_encounter, get_patient
from backend.models.pipeline import ClaimPipelineItem
from backend.models.x12 import ERA835, RemittanceLine


# Common CARC codes and their descriptions
CARC_DESCRIPTIONS: dict[str, str] = {
    "CO-4": "The procedure code is inconsistent with the modifier used or a required modifier is missing.",
    "CO-11": "The diagnosis is inconsistent with the procedure.",
    "CO-16": "Claim/service lacks information or has submission/billing error(s).",
    "CO-18": "Exact duplicate claim/service.",
    "CO-22": "This care may be covered by another payer per coordination of benefits.",
    "CO-27": "Expenses incurred after coverage terminated.",
    "CO-29": "The time limit for filing has expired.",
    "CO-50": "These are non-covered services because this is not deemed a medical necessity.",
    "CO-96": "Non-covered charge(s). At least one Remark Code must be provided.",
    "CO-97": "The benefit for this service is included in the allowance/payment for another service.",
    "CO-109": "Claim/service not covered by this payer/contractor.",
    "CO-151": "Payment adjusted because the payer deems the information submitted does not support this level of service.",
    "CO-167": "This (these) diagnosis(es) is (are) not covered.",
    "CO-197": "Precertification/authorization/notification absent.",
    "CO-204": "This service/equipment/drug is not covered under the patient's current benefit plan.",
    "CO-236": "This procedure or procedure/modifier combination is not compatible with another procedure or procedure/modifier combination provided on the same day.",
    "PR-1": "Deductible amount.",
    "PR-2": "Coinsurance amount.",
    "PR-3": "Co-payment amount.",
}


class DenialDetail(BaseModel):
    claim_id: str
    patient_id: str
    patient_name: str = ""
    carc_code: str = ""
    carc_description: str = ""
    rarc_codes: list[str] = Field(default_factory=list)
    denial_reason: str = ""
    total_charge: float = 0.0
    paid_amount: float = 0.0
    cpt_codes: list[str] = Field(default_factory=list)
    icd10_codes: list[str] = Field(default_factory=list)
    encounter_id: str = ""
    clinical_note_excerpt: str = ""
    supporting_documentation: list[str] = Field(default_factory=list)
    appeal_generated: bool = False
    appeal_text: str = ""


class DenialManager:
    """Manages claim denials: parses 835 ERA, pulls supporting docs, orchestrates appeals."""

    def parse_era(self, era: ERA835) -> DenialDetail:
        """Parse an 835 ERA and extract denial details."""
        pipeline_item = get_pipeline_item(era.claim_id)

        patient_name = ""
        if pipeline_item:
            patient_name = pipeline_item.patient_name

        carc_code = era.primary_denial_code() or ""
        carc_desc = CARC_DESCRIPTIONS.get(carc_code, "Unknown denial code.")

        return DenialDetail(
            claim_id=era.claim_id,
            patient_id=era.patient_id,
            patient_name=patient_name,
            carc_code=carc_code,
            carc_description=carc_desc,
            rarc_codes=era.rarc_codes,
            denial_reason=carc_desc,
            total_charge=era.total_charge,
            paid_amount=era.total_paid,
            cpt_codes=pipeline_item.cpt_codes if pipeline_item else [],
            icd10_codes=pipeline_item.icd10_codes if pipeline_item else [],
            encounter_id=pipeline_item.encounter_id if pipeline_item else "",
        )

    async def simulate_denial(self, claim_id: str, carc_code: str = "CO-50") -> DenialDetail | None:
        """Simulate a denial for a pipeline claim (for demo purposes)."""
        pipeline = get_pipeline()
        item = pipeline.get(claim_id)
        if not item:
            return None

        # Update pipeline status
        item.status = "denied"
        item.denial_code = carc_code
        item.denial_reason = CARC_DESCRIPTIONS.get(carc_code, "Claim denied.")
        item.updated_at = datetime.utcnow()

        # Pull supporting documentation from encounter
        clinical_note_excerpt = ""
        supporting_docs: list[str] = []
        if item.encounter_id:
            encounter = get_encounter(item.encounter_id)
            if encounter:
                clinical_note_excerpt = encounter.clinical_note[:500]
                supporting_docs.append(f"Clinical note from {encounter.date} - {encounter.provider}")
                supporting_docs.append(f"Encounter at {encounter.facility}")

        patient = get_patient(item.patient_id)
        if patient:
            if patient.conditions:
                supporting_docs.append(f"Active conditions: {', '.join(patient.conditions)}")
            if patient.medications:
                supporting_docs.append(f"Current medications: {', '.join(patient.medications[:5])}")

        return DenialDetail(
            claim_id=claim_id,
            patient_id=item.patient_id,
            patient_name=item.patient_name,
            carc_code=carc_code,
            carc_description=CARC_DESCRIPTIONS.get(carc_code, "Unknown denial code."),
            denial_reason=CARC_DESCRIPTIONS.get(carc_code, "Claim denied."),
            total_charge=item.total_charge,
            paid_amount=0.0,
            cpt_codes=item.cpt_codes,
            icd10_codes=item.icd10_codes,
            encounter_id=item.encounter_id,
            clinical_note_excerpt=clinical_note_excerpt,
            supporting_documentation=supporting_docs,
        )

    async def generate_appeal(self, denial: DenialDetail) -> DenialDetail:
        """Generate an appeal letter for a denied claim using v1 appeal system enhanced with FHIR evidence."""
        # Build enhanced clinical context from FHIR data
        clinical_context = denial.clinical_note_excerpt
        if denial.supporting_documentation:
            clinical_context += "\n\nSupporting Documentation:\n"
            clinical_context += "\n".join(f"- {doc}" for doc in denial.supporting_documentation)

        # Generate appeal text (using rule-based approach; v1 AppealWriter can be used with API key)
        appeal_text = self._generate_appeal_text(denial, clinical_context)

        denial.appeal_generated = True
        denial.appeal_text = appeal_text

        # Update pipeline item
        pipeline = get_pipeline()
        item = pipeline.get(denial.claim_id)
        if item:
            item.status = "appealed"
            item.appeal_id = f"APL-{uuid.uuid4().hex[:8].upper()}"
            item.appeal_text = appeal_text
            item.updated_at = datetime.utcnow()

        return denial

    def _generate_appeal_text(self, denial: DenialDetail, clinical_context: str) -> str:
        """Generate appeal letter text based on denial details and clinical evidence."""
        cpt_str = ", ".join(denial.cpt_codes)
        icd_str = ", ".join(denial.icd10_codes)

        letter = f"""Date: {datetime.utcnow().strftime('%m/%d/%Y')}

To: Claims Review Department
Re: Appeal of Claim {denial.claim_id} for Patient {denial.patient_name}

Dear Appeals Review Committee,

I am writing to formally appeal the denial of the above-referenced claim. The claim was denied with code {denial.carc_code}: "{denial.carc_description}"

CLAIM DETAILS:
- Procedures: {cpt_str}
- Diagnoses: {icd_str}
- Total Charge: ${denial.total_charge:,.2f}

CLINICAL JUSTIFICATION:
{clinical_context}

APPEAL BASIS:
"""
        # Customize appeal based on denial code
        if denial.carc_code == "CO-50":
            letter += """The clinical documentation clearly establishes medical necessity for the performed procedures. The patient's documented condition, treatment history, and clinical presentation all support the necessity of these services as outlined in the attached records.

Per the applicable coverage determination criteria, this patient meets all requirements for coverage of the billed services.\n"""

        elif denial.carc_code == "CO-197":
            letter += """We believe prior authorization was either obtained or should not have been required for this service. We are attaching the authorization reference and request that the claim be reprocessed accordingly.\n"""

        elif denial.carc_code in ("CO-4", "CO-236"):
            letter += """We have reviewed the coding and believe the procedure codes and modifiers are appropriate and correctly reflect the distinct services provided. The documentation supports each billed service as a separately identifiable procedure.\n"""

        elif denial.carc_code == "CO-11":
            letter += """The diagnosis codes submitted are clinically appropriate and directly support the procedures performed. The clinical documentation establishes the medical rationale linking the diagnoses to the procedures billed.\n"""

        elif denial.carc_code == "CO-29":
            letter += """We have evidence that the original claim was filed within the payer's timely filing requirement. We are attaching proof of original submission and request that the claim be reconsidered.\n"""

        else:
            letter += f"""We respectfully disagree with this denial determination. The enclosed clinical documentation supports the medical necessity and appropriateness of the billed services. We request a full review of the supporting materials.\n"""

        letter += """
REQUEST:
We respectfully request that this claim be reconsidered and reprocessed for payment based on the clinical evidence provided. Please contact our office if additional documentation is needed.

Sincerely,
Provider Office
"""
        return letter
