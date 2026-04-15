"""Load and serve synthetic FHIR data from data/fhir_patients.json."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Optional

from backend.models.fhir_types import (
    FHIRPatient,
    FHIREncounter,
    FHIRCoverage,
    HumanName,
    Address,
    Telecom,
)

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "fhir_patients.json")


@lru_cache(maxsize=1)
def _load_raw() -> dict:
    with open(DATA_PATH, "r") as f:
        return json.load(f)


def get_all_patients() -> list[FHIRPatient]:
    raw = _load_raw()
    patients = []
    for p in raw.get("patients", []):
        patients.append(FHIRPatient(
            id=p["id"],
            name=[HumanName(**n) for n in p.get("name", [])],
            gender=p.get("gender", ""),
            birthDate=p.get("birthDate", ""),
            address=[Address(**a) for a in p.get("address", [])],
            telecom=[Telecom(**t) for t in p.get("telecom", [])],
            conditions=p.get("conditions", []),
            medications=p.get("medications", []),
        ))
    return patients


def get_patient(patient_id: str) -> Optional[FHIRPatient]:
    for p in get_all_patients():
        if p.id == patient_id:
            return p
    return None


def get_all_encounters() -> list[FHIREncounter]:
    raw = _load_raw()
    encounters = []
    for e in raw.get("encounters", []):
        encounters.append(FHIREncounter(
            id=e["id"],
            patient_id=e["patient_id"],
            status=e.get("status", "finished"),
            **{"class": e.get("class", "ambulatory")},
            type=e.get("type", ""),
            date=e.get("date", ""),
            provider=e.get("provider", ""),
            facility=e.get("facility", ""),
            place_of_service=e.get("place_of_service", "11"),
            clinical_note=e.get("clinical_note", ""),
        ))
    return encounters


def get_encounter(encounter_id: str) -> Optional[FHIREncounter]:
    for e in get_all_encounters():
        if e.id == encounter_id:
            return e
    return None


def get_patient_encounters(patient_id: str) -> list[FHIREncounter]:
    return [e for e in get_all_encounters() if e.patient_id == patient_id]


def get_all_coverages() -> list[FHIRCoverage]:
    raw = _load_raw()
    coverages = []
    for c in raw.get("coverages", []):
        coverages.append(FHIRCoverage(**c))
    return coverages


def get_coverage(coverage_id: str) -> Optional[FHIRCoverage]:
    for c in get_all_coverages():
        if c.id == coverage_id:
            return c
    return None


def get_patient_coverage(patient_id: str) -> Optional[FHIRCoverage]:
    for c in get_all_coverages():
        if c.patient_id == patient_id:
            return c
    return None
