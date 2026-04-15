"""Coverage verification agent — checks patient eligibility from FHIR data."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from backend.fhir.seed_data import get_patient, get_patient_coverage


class EligibilityResult(BaseModel):
    patient_id: str
    eligible: bool = False
    payer: str = ""
    payer_name: str = ""
    plan: str = ""
    member_id: str = ""
    group: str = ""
    copay: float = 0
    deductible: float = 0
    deductible_met: float = 0
    deductible_remaining: float = 0
    coverage_active: bool = False
    period_start: str = ""
    period_end: str = ""
    issues: list[str] = Field(default_factory=list)


class EligibilityAgent:
    """Verifies patient coverage eligibility using FHIR Coverage data."""

    async def verify(self, patient_id: str, date_of_service: str = "") -> EligibilityResult:
        patient = get_patient(patient_id)
        if not patient:
            return EligibilityResult(
                patient_id=patient_id,
                eligible=False,
                issues=["Patient not found in system."],
            )

        coverage = get_patient_coverage(patient_id)
        if not coverage:
            return EligibilityResult(
                patient_id=patient_id,
                eligible=False,
                issues=["No active coverage found for patient."],
            )

        issues: list[str] = []
        coverage_active = coverage.status == "active"

        # Check if date of service falls within coverage period
        if date_of_service and coverage.period_start and coverage.period_end:
            try:
                dos = datetime.strptime(date_of_service, "%Y-%m-%d")
                start = datetime.strptime(coverage.period_start, "%Y-%m-%d")
                end = datetime.strptime(coverage.period_end, "%Y-%m-%d")
                if dos < start or dos > end:
                    coverage_active = False
                    issues.append(
                        f"Date of service {date_of_service} falls outside coverage period "
                        f"({coverage.period_start} to {coverage.period_end})."
                    )
            except ValueError:
                pass

        if not coverage_active:
            issues.append("Coverage is not active.")

        deductible_remaining = max(0, coverage.deductible - coverage.deductible_met)
        if deductible_remaining > 0:
            issues.append(f"Patient has ${deductible_remaining:.2f} remaining on deductible.")

        return EligibilityResult(
            patient_id=patient_id,
            eligible=coverage_active and len([i for i in issues if "not active" in i or "outside" in i]) == 0,
            payer=coverage.payer,
            payer_name=coverage.payer_name,
            plan=coverage.plan,
            member_id=coverage.member_id,
            group=coverage.group,
            copay=coverage.copay,
            deductible=coverage.deductible,
            deductible_met=coverage.deductible_met,
            deductible_remaining=deductible_remaining,
            coverage_active=coverage_active,
            period_start=coverage.period_start,
            period_end=coverage.period_end,
            issues=issues,
        )
