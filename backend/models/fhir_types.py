"""FHIR R4 Pydantic models for ClaimPilot v2."""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class HumanName(BaseModel):
    family: str
    given: list[str] = Field(default_factory=list)

    @property
    def full_name(self) -> str:
        return f"{' '.join(self.given)} {self.family}"


class Address(BaseModel):
    line: list[str] = Field(default_factory=list)
    city: str = ""
    state: str = ""
    postalCode: str = ""


class Telecom(BaseModel):
    system: str = "phone"
    value: str = ""


class FHIRPatient(BaseModel):
    resourceType: str = "Patient"
    id: str
    name: list[HumanName] = Field(default_factory=list)
    gender: str = ""
    birthDate: str = ""
    address: list[Address] = Field(default_factory=list)
    telecom: list[Telecom] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list)


class FHIREncounter(BaseModel):
    resourceType: str = "Encounter"
    id: str
    patient_id: str
    status: str = "finished"
    encounter_class: str = Field(default="ambulatory", alias="class")
    type: str = ""
    date: str = ""
    provider: str = ""
    facility: str = ""
    place_of_service: str = "11"
    clinical_note: str = ""

    model_config = {"populate_by_name": True}


class FHIRCoverage(BaseModel):
    resourceType: str = "Coverage"
    id: str
    patient_id: str
    status: str = "active"
    payer: str = ""
    payer_name: str = ""
    plan: str = ""
    member_id: str = ""
    group: str = ""
    period_start: str = ""
    period_end: str = ""
    copay: float = 0
    deductible: float = 0
    deductible_met: float = 0


class FHIRClaim(BaseModel):
    resourceType: str = "Claim"
    id: str
    patient_id: str
    encounter_id: str
    status: str = "active"
    type: str = "professional"
    provider: str = ""
    payer: str = ""
    cpt_codes: list[str] = Field(default_factory=list)
    icd10_codes: list[str] = Field(default_factory=list)
    total_charge: float = 0.0
    date_of_service: str = ""
    place_of_service: str = "11"


class FHIRBundle(BaseModel):
    resourceType: str = "Bundle"
    type: str = "searchset"
    total: int = 0
    entry: list[dict] = Field(default_factory=list)
