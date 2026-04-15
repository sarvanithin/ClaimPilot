"""CPT/ICD-10 code mapping and modifier logic for charge capture and scrubbing."""

from __future__ import annotations

import json
import os
from functools import lru_cache

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")


@lru_cache(maxsize=1)
def load_cpt_codes() -> dict[str, dict]:
    path = os.path.join(DATA_DIR, "cpt_codes.json")
    with open(path, "r") as f:
        codes = json.load(f)
    return {c["code"]: c for c in codes}


@lru_cache(maxsize=1)
def load_icd10_codes() -> dict[str, dict]:
    path = os.path.join(DATA_DIR, "icd10_codes.json")
    with open(path, "r") as f:
        codes = json.load(f)
    return {c["code"]: c for c in codes}


def get_cpt_description(code: str) -> str:
    codes = load_cpt_codes()
    entry = codes.get(code)
    return entry["description"] if entry else f"Unknown CPT {code}"


def get_cpt_charge(code: str) -> float:
    codes = load_cpt_codes()
    entry = codes.get(code)
    return entry["typical_charge"] if entry else 0.0


def get_icd10_description(code: str) -> str:
    codes = load_icd10_codes()
    entry = codes.get(code)
    return entry["description"] if entry else f"Unknown ICD-10 {code}"


def is_em_code(code: str) -> bool:
    """Check if a CPT code is an E&M code."""
    return code.startswith("992") or code.startswith("993")


def is_surgical_code(code: str) -> bool:
    """Check if a CPT is in the surgical range (10000-69999)."""
    try:
        num = int(code)
        return 10000 <= num <= 69999
    except ValueError:
        return False


def needs_modifier_25(cpt_codes: list[str]) -> bool:
    """Check if an E&M code needs modifier -25 (same-day procedure)."""
    has_em = any(is_em_code(c) for c in cpt_codes)
    has_procedure = any(is_surgical_code(c) for c in cpt_codes)
    return has_em and has_procedure


# Common CPT-ICD medical necessity linkages
MEDICAL_NECESSITY_MAP: dict[str, list[str]] = {
    "27447": ["M17.11", "M17.12", "M17.9"],  # TKA -> knee OA
    "27130": ["M16.11", "M16.12", "M16.9"],  # THA -> hip OA
    "29881": ["M23.21", "M23.22", "S83.511A", "S83.512A"],  # Knee scope -> meniscus
    "29880": ["M23.21", "M23.22", "S83.511A", "S83.512A"],
    "47562": ["K80.20", "K80.10", "K80.00"],  # Cholecystectomy -> gallstones
    "47563": ["K80.20", "K80.10", "K80.00"],
    "45378": ["Z12.11", "K63.5", "K57.30"],  # Colonoscopy
    "45380": ["Z12.11", "K63.5", "K57.30", "K57.31"],
    "43239": ["K21.0", "K25.9", "R10.9"],  # EGD
    "66984": ["H25.11", "H25.12", "H25.9"],  # Cataract
    "64483": ["M54.5", "M54.41", "M54.42", "G89.29"],  # Epidural
    "93458": ["I25.10", "I25.11", "I48.91"],  # Cardiac cath
    "49505": ["K40.90", "K40.91"],  # Hernia repair
    "90834": ["F32.1", "F32.2", "F41.1", "F10.20"],  # Psychotherapy
    "90837": ["F32.1", "F32.2", "F41.1", "F10.20"],
}


def check_medical_necessity(cpt_code: str, icd10_codes: list[str]) -> bool:
    """Check if at least one ICD-10 code supports medical necessity for the CPT."""
    allowed = MEDICAL_NECESSITY_MAP.get(cpt_code)
    if allowed is None:
        # No specific mapping; assume acceptable for E&M and lab codes
        return True
    return any(icd in allowed for icd in icd10_codes)


def suggest_icd10_for_cpt(cpt_code: str) -> list[str]:
    """Suggest ICD-10 codes that support a given CPT."""
    return MEDICAL_NECESSITY_MAP.get(cpt_code, [])
