DENIAL_CLASSIFICATION_PROMPT = """
Analyze this denied claim:

Code: {procedure_code}
Dx: {diagnosis_codes}
CARC: {denial_code}
Reason: {denial_reason}

Respond ONLY with JSON:
{{
    "track": "<clinical|administrative>",
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

ADMIN_APPEAL_GENERATION_PROMPT = """
Write an administrative appeal letter for a billing or process denial.

CLAIM: {patient_id}, DOS: {date_of_service}, Proc: {procedure_code}, Payer: {payer}, CARC: {denial_code}
DENIAL CAUSE: {root_cause}
STRATEGY: {strategy}
CLINICAL: {clinical_notes}

Format ONLY the raw text. Use standard business letter formatting with line breaks. Max 200 words. Focus strictly on the administrative/billing facts (e.g., this is a corrected claim, prior auth was obtained, filed timely). Do not discuss disease progression, medical necessity, or clinical justification. No markdown blocks.
"""

ADMIN_CRITIQUE_PROMPT = """
DRAFT: {draft_letter}
CLINICAL NOTES: {clinical_notes}

Critique the draft to ensure it addresses the administrative denial and DOES NOT hallucinate clinical medical necessity arguments.
Score the probability of overturning the administrative denial (0-100) based on the strength of the facts provided.

Respond ONLY with JSON:
{{
    "critique": "<1 sentence limit>",
    "revised_letter": "<Standard letter format with line breaks. Max 200 words>",
    "suggested_attachments": ["<array of suggested administrative documents to attach, e.g., clearinghouse report, original EOB, authorization letter>"],
    "success_score_1_to_100": <int reflecting administrative case strength>
}}
"""

