DENIAL_CLASSIFICATION_PROMPT = """
Analyze this denied claim:

Code: {procedure_code}
Dx: {diagnosis_codes}
CARC: {denial_code}
Reason: {denial_reason}

Respond ONLY with JSON:
{{
    "category": "<medical_necessity|coding_error|auth_missing|timely_filing|documentation|duplicate|non_covered>",
    "confidence": <float 0.0-1.0>,
    "reasoning": "<1 sentence constraint>"
}}
"""

APPEAL_GENERATION_PROMPT = """
Write an appeal letter.

CLAIM: {patient_id}, DOS: {date_of_service}, Proc: {procedure_code}, Dx: {diagnosis_codes}, Payer: {payer}, CARC: {denial_code}
DENIAL CAUSE: {root_cause}
STRATEGY: {strategy}
POLICIES: {policy_citations}
CLINICAL: {clinical_notes}

Format ONLY the raw text. Use standard business letter formatting with line breaks. Max 200 words. Be concise, cite policies. No markdown blocks.
"""

SELF_CRITIQUE_PROMPT = """
DRAFT: {draft_letter}
POLICIES: {policy_citations}
CLINICAL NOTES: {clinical_notes}

Critique the draft against the policies. Identify any required evidence from the policies that is missing in the clinical notes.
Score the probability of overturning the denial (0-100) based strictly on whether the clinical notes satisfy the policy requirements.

Respond ONLY with JSON:
{{
    "critique": "<1 sentence limit>",
    "revised_letter": "<Standard letter format with line breaks. Max 200 words>",
    "missing_evidence": ["<array of missing criteria>"],
    "success_score_1_to_100": <int reflecting evidence strength>
}}
"""
