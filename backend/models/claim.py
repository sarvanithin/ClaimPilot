from pydantic import BaseModel, Field
from typing import Optional, List

class Claim(BaseModel):
    """Input claim data representing a denied claim"""
    patient_id: str = Field(..., description="Anonymized patient identifier")
    procedure_code: str = Field(..., description="CPT code (e.g., '99213')")
    diagnosis_codes: List[str] = Field(..., description="ICD-10 codes (e.g., ['E11.9', 'I10'])")
    payer: str = Field(..., description="Insurance company name")
    denial_code: str = Field(..., description="CARC code (e.g., 'CO-4', 'CO-197')")
    denial_reason: str = Field(..., description="Free-text from payer explaining denial")
    date_of_service: str = Field(..., description="Format: MM/DD/YYYY")
    provider_name: str = Field(..., description="Name of the healthcare provider/facility")
    clinical_notes: Optional[str] = Field(None, description="Optional supporting clinical documentation")

class PolicyReference(BaseModel):
    """Reference to a specific section of a policy document"""
    source: str = Field(..., description="'CMS LCD L35041' or 'UHC Policy 2024-045'")
    section: str = Field(..., description="Specific section/paragraph number")
    text: str = Field(..., description="Relevant excerpt from the policy")
    relevance: str = Field(..., description="Explanation of why this supports the appeal")

class DenialAnalysis(BaseModel):
    """Agent's analysis of the denial"""
    track: str = Field(..., description="'clinical' | 'administrative'")
    denial_category: str = Field(..., description="'medical_necessity' | 'coding_error' | 'auth_missing' | 'timely_filing' | 'documentation'")
    denial_code: str = Field(..., description="The CARC code")
    denial_description: str = Field(..., description="Standard description of the CARC code")
    root_cause: str = Field(..., description="Agent's analysis of why it was denied based on inputs")
    appeal_strategy: str = Field(..., description="Recommended approach for the appeal")
    relevant_policies: List[PolicyReference] = Field(default_factory=list, description="List of cited policies")
    success_probability: str = Field(..., description="'high' | 'medium' | 'low'")

class AppealLetter(BaseModel):
    """The generated appeal letter and metadata"""
    subject_line: str = Field(..., description="Email or letter subject")
    date: str = Field(..., description="Date of the appeal")
    payer_address: str = Field(..., description="Payer's appeals department address (mocked if unknown)")
    re_line: str = Field(..., description="e.g., 'Re: Appeal of Claim #12345, DOS 01/15/2024'")
    opening: str = Field(..., description="Formal opening paragraph")
    medical_necessity: str = Field(..., description="Clinical justification section")
    policy_citations: str = Field(..., description="Cited policy references formatted nicely")
    conclusion: str = Field(..., description="Closing + requested action")
    attachments_needed: List[str] = Field(default_factory=list, description="What supporting docs to include")
    missing_evidence: List[str] = Field(default_factory=list, description="Clinical gaps identified vs policy")
    success_score_1_to_100: int = Field(50, description="Estimated probability of overturning the denial")
    full_text: str = Field(..., description="Complete, fully formatted letter ready to be copied")

class AppealResult(BaseModel):
    """The final output returned to the frontend"""
    analysis: DenialAnalysis
    policies: List[PolicyReference]
    appeal: AppealLetter
