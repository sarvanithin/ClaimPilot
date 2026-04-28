"""Seed the in-memory pipeline with demo claims so the UI isn't empty on startup."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

from backend.agents.charge_capture import ChargeCaptureAgent
from backend.agents.claim_scrubber import ClaimScrubber
from backend.agents.claim_submitter import ClaimSubmitter, get_pipeline
from backend.agents.denial_manager import DenialManager
from backend.fhir.seed_data import get_encounter, get_patient, get_patient_coverage

# Encounters to process through the pipeline with their final statuses
_DEMO_SCENARIOS = [
    # (patient_id, encounter_id, final_status, denial_code)
    ("pat-002", "enc-004", "submitted", None),          # Maria — office visit, clean submit
    ("pat-003", "enc-007", "submitted", None),           # James — cardiac cath, submitted
    ("pat-004", "enc-009", "denied", "CO-50"),           # Lisa — procedure, denied med necessity
    ("pat-005", "enc-010", "denied", "CO-197"),          # David — ophthalmology, denied no auth
    ("pat-001", "enc-003", "appealed", "CO-50"),         # Robert — surgery, appealed
    ("pat-006", "enc-012", "paid", None),                # Sarah — routine, paid
]


async def seed_pipeline() -> int:
    """Run demo claims through the pipeline. Returns count of seeded claims."""
    pipeline = get_pipeline()
    if pipeline:
        return 0  # Already seeded

    charge_agent = ChargeCaptureAgent()
    scrubber = ClaimScrubber()
    submitter = ClaimSubmitter()
    denial_mgr = DenialManager()

    seeded = 0

    for patient_id, encounter_id, final_status, denial_code in _DEMO_SCENARIOS:
        encounter = get_encounter(encounter_id)
        patient = get_patient(patient_id)
        if not encounter or not patient:
            continue

        coverage = get_patient_coverage(patient_id)
        payer = coverage.payer if coverage else "UHC"

        try:
            # Step 1: Charge capture
            charge_result = await charge_agent.capture(
                encounter_id=encounter_id,
                clinical_note=encounter.clinical_note,
                encounter_type=encounter.type,
            )

            if not charge_result.cpt_codes:
                continue

            # Step 2: Scrub
            modifiers = {c.code: c.modifier for c in charge_result.cpt_codes if c.modifier}
            scrub_result = await scrubber.scrub(
                cpt_codes=[c.code for c in charge_result.cpt_codes],
                icd10_codes=[c.code for c in charge_result.icd10_codes],
                payer=payer,
                modifiers=modifiers,
                date_of_service=encounter.date,
            )

            # Step 3: Generate 837P
            claim_837p = await submitter.generate_837p(charge_result, patient_id)

            # Step 4: Submit
            item = await submitter.submit_to_pipeline(
                claim_837p, encounter_id, scrub_result
            )

            # Step 5: Advance to final status
            if final_status == "denied" and denial_code:
                await denial_mgr.simulate_denial(item.id, denial_code)
            elif final_status == "appealed" and denial_code:
                await denial_mgr.simulate_denial(item.id, denial_code)
                denial = await denial_mgr.simulate_denial(item.id, denial_code)
                if denial:
                    await denial_mgr.generate_appeal(denial)
            elif final_status == "paid":
                item.status = "paid"
                item.paid_amount = item.total_charge * 0.82  # Simulate 82% reimbursement
                item.updated_at = datetime.utcnow()

            seeded += 1
        except Exception as e:
            print(f"[seed] Skipping {encounter_id}: {e}")
            continue

    return seeded
