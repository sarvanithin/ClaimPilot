"""Charge Capture Agent — extracts CPT/ICD-10 codes from clinical encounter notes."""

from __future__ import annotations

import json
import re
from typing import Optional

from backend.config import settings
from backend.models.pipeline import ChargeCaptureResult, CPTCode, ICD10Code
from backend.rules.cpt_icd_map import (
    load_cpt_codes,
    load_icd10_codes,
    get_cpt_charge,
    get_cpt_description,
    get_icd10_description,
)

# Keywords mapped to CPT codes for rule-based fallback
_PROCEDURE_KEYWORDS: dict[str, str] = {
    "total knee arthroplasty": "27447",
    "total knee replacement": "27447",
    "tka": "27447",
    "total hip arthroplasty": "27130",
    "total hip replacement": "27130",
    "arthroscopy": "29881",
    "arthroscopic": "29881",
    "meniscectomy": "29881",
    "meniscus repair": "29880",
    "cholecystectomy": "47562",
    "laparoscopic cholecystectomy": "47562",
    "cholangiography": "47563",
    "colonoscopy": "45378",
    "colonoscopy with biopsy": "45380",
    "polypectomy": "45380",
    "upper gi endoscopy": "43239",
    "egd": "43239",
    "endoscopy with biopsy": "43239",
    "cataract surgery": "66984",
    "cataract extraction": "66984",
    "iol implant": "66984",
    "cardiac catheterization": "93458",
    "left heart catheterization": "93458",
    "heart catheterization": "93458",
    "epidural steroid injection": "64483",
    "transforaminal epidural": "64483",
    "epidural injection": "64483",
    "hernia repair": "49505",
    "inguinal hernia repair": "49505",
    "incision and drainage": "10060",
    "i&d": "10060",
    "excisional biopsy": "11102",
    "shave biopsy": "11102",
    "psychotherapy": "90837",
    "psychotherapy, 60": "90837",
    "psychotherapy, 45": "90834",
    "45-minute": "90834",
    "60-minute": "90837",
    "electrocardiogram": "93000",
    "ekg": "93000",
    "ecg": "93000",
    "echocardiography": "93306",
    "stress echo": "93306",
    "chest x-ray": "71046",
    "cxr": "71046",
    "mri knee": "73721",
    "mri brain": "70553",
    "ct abdomen": "74177",
    "venipuncture": "36415",
    "injection": "96372",
    "arthrocentesis": "20610",
}

# Keywords mapped to ICD-10 codes for rule-based fallback
_DIAGNOSIS_KEYWORDS: dict[str, str] = {
    "knee osteoarthritis": "M17.11",
    "right knee osteoarthritis": "M17.11",
    "right knee oa": "M17.11",
    "left knee osteoarthritis": "M17.12",
    "left knee oa": "M17.12",
    "osteoarthritis": "M17.11",
    "hip osteoarthritis": "M16.11",
    "right hip oa": "M16.11",
    "left hip oa": "M16.12",
    "meniscus tear": "M23.21",
    "meniscal tear": "M23.21",
    "acl tear": "S83.511A",
    "anterior cruciate": "S83.511A",
    "low back pain": "M54.5",
    "lumbago": "M54.5",
    "sciatica": "M54.41",
    "disc herniation": "M54.41",
    "gallstone": "K80.20",
    "cholelithiasis": "K80.20",
    "cholecystitis": "K80.10",
    "gerd": "K21.0",
    "reflux": "K21.0",
    "diverticulosis": "K57.30",
    "colon polyp": "K63.5",
    "polyp": "K63.5",
    "type 2 diabetes": "E11.9",
    "t2dm": "E11.9",
    "diabetes mellitus": "E11.9",
    "hyperglycemia": "E11.65",
    "diabetic neuropathy": "E11.40",
    "hyperlipidemia": "E78.5",
    "hypothyroidism": "E03.9",
    "hypertension": "I10",
    "htn": "I10",
    "coronary artery disease": "I25.10",
    "cad": "I25.10",
    "atrial fibrillation": "I48.91",
    "afib": "I48.91",
    "heart failure": "I50.9",
    "chf": "I50.9",
    "cerebral infarction": "I63.9",
    "stroke": "I63.9",
    "uri": "J06.9",
    "upper respiratory": "J06.9",
    "pneumonia": "J18.9",
    "copd": "J44.1",
    "copd exacerbation": "J44.1",
    "asthma": "J45.20",
    "uti": "N39.0",
    "urinary tract infection": "N39.0",
    "ckd": "N18.3",
    "chronic kidney": "N18.3",
    "depression": "F32.1",
    "major depressive": "F32.1",
    "mdd": "F32.1",
    "anxiety": "F41.1",
    "generalized anxiety": "F41.1",
    "alcohol": "F10.20",
    "alcohol dependence": "F10.20",
    "migraine": "G43.909",
    "chronic pain": "G89.29",
    "cataract": "H25.11",
    "nuclear cataract": "H25.11",
    "glaucoma": "H40.11",
    "cellulitis": "L03.311",
    "abscess": "L02.211",
    "melanocytic": "D22.5",
    "basal cell": "C44.41",
    "bcc": "C44.41",
    "inguinal hernia": "K40.90",
    "hernia": "K40.90",
    "screening colonoscopy": "Z12.11",
}

# Place of service mapping
_POS_KEYWORDS: dict[str, str] = {
    "office": "11",
    "ambulatory": "11",
    "outpatient": "22",
    "inpatient": "21",
    "hospital": "21",
    "emergency": "23",
    "ed ": "23",
    "surgical center": "24",
    "ambulatory surgical": "24",
}


class ChargeCaptureAgent:
    """Extracts procedure and diagnosis codes from clinical encounter notes."""

    async def capture(self, encounter_id: str, clinical_note: str, encounter_type: str = "") -> ChargeCaptureResult:
        """
        Extract charges from a clinical note.
        Uses rule-based extraction (Claude API integration available but optional).
        """
        return self._rule_based_capture(encounter_id, clinical_note, encounter_type)

    def _rule_based_capture(
        self, encounter_id: str, clinical_note: str, encounter_type: str = ""
    ) -> ChargeCaptureResult:
        note_lower = clinical_note.lower()

        # Extract CPT codes
        cpt_codes: list[CPTCode] = []
        seen_cpts: set[str] = set()

        for keyword, code in _PROCEDURE_KEYWORDS.items():
            if keyword in note_lower and code not in seen_cpts:
                seen_cpts.add(code)
                cpt_codes.append(CPTCode(
                    code=code,
                    description=get_cpt_description(code),
                    modifier="",
                    confidence=0.85,
                    charge=get_cpt_charge(code),
                ))

        # If no specific procedure found, try to assign an E&M code based on encounter type
        if not cpt_codes or all(not c.code.startswith("9") for c in cpt_codes):
            em_code = self._infer_em_code(note_lower, encounter_type)
            if em_code and em_code not in seen_cpts:
                seen_cpts.add(em_code)
                cpt_codes.insert(0, CPTCode(
                    code=em_code,
                    description=get_cpt_description(em_code),
                    modifier="",
                    confidence=0.75,
                    charge=get_cpt_charge(em_code),
                ))

        # Check for modifier -25 (E&M with same-day procedure)
        has_em = any(c.code.startswith("992") or c.code.startswith("993") for c in cpt_codes)
        has_proc = any(not (c.code.startswith("992") or c.code.startswith("993")) for c in cpt_codes)
        if has_em and has_proc:
            for c in cpt_codes:
                if c.code.startswith("992") or c.code.startswith("993"):
                    c.modifier = "-25"

        # Extract ICD-10 codes
        icd10_codes: list[ICD10Code] = []
        seen_icds: set[str] = set()

        for keyword, code in _DIAGNOSIS_KEYWORDS.items():
            if keyword in note_lower and code not in seen_icds:
                seen_icds.add(code)
                icd10_codes.append(ICD10Code(
                    code=code,
                    description=get_icd10_description(code),
                    confidence=0.80,
                ))

        # Also check for explicit ICD-10 codes mentioned in text (e.g., "M17.11")
        icd10_pattern = re.compile(r'\b([A-Z]\d{2}\.\d{1,4}[A-Z]?)\b')
        for match in icd10_pattern.finditer(clinical_note):
            code = match.group(1)
            if code not in seen_icds:
                seen_icds.add(code)
                icd10_codes.append(ICD10Code(
                    code=code,
                    description=get_icd10_description(code),
                    confidence=0.95,
                ))

        # Determine place of service
        pos = "11"  # default office
        for keyword, pos_code in _POS_KEYWORDS.items():
            if keyword in note_lower:
                pos = pos_code
                break

        total_charge = sum(c.charge for c in cpt_codes)

        return ChargeCaptureResult(
            encounter_id=encounter_id,
            cpt_codes=cpt_codes,
            icd10_codes=icd10_codes,
            place_of_service=pos,
            total_estimated_charge=total_charge,
        )

    def _infer_em_code(self, note_lower: str, encounter_type: str) -> str | None:
        """Infer an E&M code from encounter type and note complexity."""
        et = encounter_type.lower()

        # ED visits
        if "emergency" in et or "ed visit" in et:
            if any(w in note_lower for w in ["threat to life", "critical", "stemi", "intubat"]):
                return "99285"
            elif any(w in note_lower for w in ["high severity", "admitted", "acute"]):
                return "99284"
            elif "moderate" in note_lower:
                return "99283"
            return "99283"

        # Inpatient
        if "hospital" in et or "inpatient" in et or "admission" in et:
            if any(w in note_lower for w in ["high complexity", "icu", "critical"]):
                return "99223"
            elif "moderate" in note_lower:
                return "99222"
            return "99221"

        # Office visits
        if any(w in note_lower for w in ["new patient", "initial consultation"]):
            if any(w in note_lower for w in ["high complexity", "multiple comorbidities"]):
                return "99205"
            elif any(w in note_lower for w in ["moderate complexity", "several"]):
                return "99204"
            return "99203"

        # Default established patient
        note_length = len(note_lower)
        if note_length > 1500 or any(w in note_lower for w in ["multiple", "comorbid", "complex"]):
            return "99215"
        elif note_length > 800:
            return "99214"
        elif note_length > 400:
            return "99213"
        return "99212"
