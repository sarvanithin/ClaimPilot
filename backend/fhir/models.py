"""Re-export FHIR models for convenience."""

from backend.models.fhir_types import (
    FHIRPatient,
    FHIREncounter,
    FHIRCoverage,
    FHIRClaim,
    FHIRBundle,
    HumanName,
    Address,
    Telecom,
)

__all__ = [
    "FHIRPatient",
    "FHIREncounter",
    "FHIRCoverage",
    "FHIRClaim",
    "FHIRBundle",
    "HumanName",
    "Address",
    "Telecom",
]
