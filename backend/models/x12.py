"""X12 837P/835 claim models for electronic claim submission and remittance."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ServiceLine(BaseModel):
    """Single line item on an 837P claim."""
    line_number: int
    cpt_code: str
    modifier: str = ""
    icd10_pointers: list[int] = Field(default_factory=list)
    units: int = 1
    charge_amount: float = 0.0
    place_of_service: str = "11"
    date_of_service: str = ""


class Claim837P(BaseModel):
    """Professional claim in 837P format."""
    claim_id: str
    patient_id: str
    patient_name: str = ""
    patient_dob: str = ""
    patient_gender: str = ""
    subscriber_id: str = ""
    payer_id: str = ""
    payer_name: str = ""
    provider_npi: str = "1234567890"
    provider_name: str = ""
    provider_tax_id: str = "12-3456789"
    facility_name: str = ""
    facility_npi: str = "0987654321"
    diagnosis_codes: list[str] = Field(default_factory=list)
    service_lines: list[ServiceLine] = Field(default_factory=list)
    total_charge: float = 0.0
    place_of_service: str = "11"
    frequency_code: str = "1"  # 1=original, 7=replacement, 8=void

    def to_x12_summary(self) -> dict:
        """Return a summary representation of the 837P claim."""
        return {
            "claim_id": self.claim_id,
            "patient": self.patient_name,
            "payer": self.payer_name,
            "total_charge": self.total_charge,
            "service_lines": len(self.service_lines),
            "diagnosis_codes": self.diagnosis_codes,
            "cpt_codes": [sl.cpt_code for sl in self.service_lines],
        }


class RemittanceLine(BaseModel):
    """Single line from an 835 ERA remittance."""
    line_number: int
    cpt_code: str
    charge_amount: float = 0.0
    paid_amount: float = 0.0
    adjustment_amount: float = 0.0
    carc_code: str = ""
    rarc_code: str = ""
    remark: str = ""


class ERA835(BaseModel):
    """Electronic Remittance Advice in 835 format."""
    era_id: str
    claim_id: str
    patient_id: str
    payer_name: str = ""
    check_number: str = ""
    check_date: str = ""
    total_charge: float = 0.0
    total_paid: float = 0.0
    total_adjustment: float = 0.0
    claim_status: str = ""  # "paid" | "denied" | "partial"
    remittance_lines: list[RemittanceLine] = Field(default_factory=list)
    carc_codes: list[str] = Field(default_factory=list)
    rarc_codes: list[str] = Field(default_factory=list)

    def is_denied(self) -> bool:
        return self.claim_status == "denied" or self.total_paid == 0

    def primary_denial_code(self) -> str | None:
        if self.carc_codes:
            return self.carc_codes[0]
        return None
