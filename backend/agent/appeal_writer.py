import json
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from backend.models.claim import Claim, DenialAnalysis, PolicyReference, AppealLetter
from backend.agent.prompts import (
    APPEAL_GENERATION_PROMPT, SELF_CRITIQUE_PROMPT,
    ADMIN_APPEAL_GENERATION_PROMPT, ADMIN_CRITIQUE_PROMPT
)
from backend.config import settings

class AppealWriter:
    def __init__(self):
        # We need a highly capable model for text generation and self-critique
        self.llm = ChatGroq(
            model=settings.DEFAULT_MODEL,
            temperature=0.2, 
            max_tokens=600, # optimized token limit
            api_key=settings.GROQ_API_KEY if settings.GROQ_API_KEY else "dummy_key",
        )
        self.critique_llm = ChatGroq(
            model=settings.DEFAULT_MODEL,
            temperature=0.0,
            max_tokens=1000, # optimized token limit
            api_key=settings.GROQ_API_KEY if settings.GROQ_API_KEY else "dummy_key",
            model_kwargs={"response_format": {"type": "json_object"}}
        )
        self.appeal_prompt = PromptTemplate(
            input_variables=["patient_id", "date_of_service", "procedure_code", "diagnosis_codes", 
                             "payer", "denial_code", "root_cause", "strategy", "policy_citations", "clinical_notes"],
            template=APPEAL_GENERATION_PROMPT
        )
        self.critique_prompt = PromptTemplate(
            input_variables=["draft_letter", "policy_citations", "clinical_notes"],
            template=SELF_CRITIQUE_PROMPT
        )
        self.admin_appeal_prompt = PromptTemplate(
            input_variables=["patient_id", "date_of_service", "procedure_code", 
                             "payer", "denial_code", "root_cause", "strategy", "clinical_notes"],
            template=ADMIN_APPEAL_GENERATION_PROMPT
        )
        self.admin_critique_prompt = PromptTemplate(
            input_variables=["draft_letter", "clinical_notes"],
            template=ADMIN_CRITIQUE_PROMPT
        )

    def write_appeal(self, claim: Claim, analysis: DenialAnalysis, policies: list[PolicyReference]) -> AppealLetter:
        """Generates the initial appeal letter, then refines it via self-critique"""
        
        if not settings.GROQ_API_KEY:
            return self._mock_appeal(claim, analysis)
            
        policy_texts = "\n\n".join([f"[{p.source} - {p.section}]: {p.text}" for p in policies])
        
        # Branch based on track
        if analysis.track == "clinical":
            chain = self.appeal_prompt | self.llm
            draft_response = chain.invoke({
                "patient_id": claim.patient_id,
                "date_of_service": claim.date_of_service,
                "procedure_code": claim.procedure_code,
                "diagnosis_codes": ", ".join(claim.diagnosis_codes),
                "payer": claim.payer,
                "denial_code": claim.denial_code,
                "root_cause": analysis.root_cause,
                "strategy": analysis.appeal_strategy,
                "policy_citations": policy_texts,
                "clinical_notes": claim.clinical_notes or "No additional clinical notes provided."
            })
            
            draft_letter = draft_response.content
            
            critique_chain = self.critique_prompt | self.critique_llm
            critique_response = critique_chain.invoke({
                "draft_letter": draft_letter,
                "policy_citations": policy_texts,
                "clinical_notes": claim.clinical_notes or "No additional clinical notes provided."
            })
        else: # administrative
            chain = self.admin_appeal_prompt | self.llm
            draft_response = chain.invoke({
                "patient_id": claim.patient_id,
                "date_of_service": claim.date_of_service,
                "procedure_code": claim.procedure_code,
                "payer": claim.payer,
                "denial_code": claim.denial_code,
                "root_cause": analysis.root_cause,
                "strategy": analysis.appeal_strategy,
                "clinical_notes": claim.clinical_notes or "No additional information provided."
            })
            
            draft_letter = draft_response.content
            
            critique_chain = self.admin_critique_prompt | self.critique_llm
            critique_response = critique_chain.invoke({
                "draft_letter": draft_letter,
                "clinical_notes": claim.clinical_notes or "No additional information provided."
            })
        
        try:
            critique_result = json.loads(critique_response.content)
            final_letter = critique_result.get("revised_letter", draft_letter)
            missing_evidence = critique_result.get("missing_evidence", [])
            suggested_attachments = critique_result.get("suggested_attachments", [])
            success_score = critique_result.get("success_score_1_to_100", 50)
            print(f"Critique Output: {critique_result.get('critique', 'No critique noted')}")
        except Exception as e:
            print(f"Critique parsing failed: {e}")
            final_letter = draft_letter
            missing_evidence = []
            suggested_attachments = []
            success_score = 50
            
        return self._build_appeal_response(claim, final_letter, missing_evidence, suggested_attachments, success_score, analysis.track)
        
    def _build_appeal_response(self, claim: Claim, full_text: str, missing_evidence: list[str], suggested_attachments: list[str], success_score: int, track: str) -> AppealLetter:
        return AppealLetter(
            subject_line=f"Appeal for Claim #{claim.patient_id[:5]}",
            date="Today",
            payer_address="Claims Review Department",
            re_line=f"Re: Appeal of Claim for Patient {claim.patient_id}, DOS {claim.date_of_service}",
            opening="Dear Appeals Department,",
            medical_necessity="See full text for details." if track == "clinical" else "N/A - Administrative issue.",
            policy_citations="See full text for citations." if track == "clinical" else "N/A - Administrative issue.",
            conclusion="Thank you for your prompt attention to this matter.",
            attachments_needed=suggested_attachments if suggested_attachments else (["Clinical Notes", "Operative Report"] if track == "clinical" else ["Claim Form", "Proof of Timely Filing"]),
            missing_evidence=missing_evidence,
            success_score_1_to_100=success_score,
            full_text=full_text
        )

    def _mock_appeal(self, claim: Claim, analysis: DenialAnalysis) -> AppealLetter:
        """Fallback mock for UI testing"""
        mock_text = f"""Date: {claim.date_of_service}
To: {claim.payer} Appeals Department
Re: Appeal of Claim for Patient {claim.patient_id}

Dear Claims Review Department,

I am writing to formally appeal the denial of procedure {claim.procedure_code} for date of service {claim.date_of_service}. The claim was denied with code {claim.denial_code}.

Based on our analysis, the denial states: "{analysis.denial_description}". However, clinical documentation clearly demonstrates medical necessity.

{claim.clinical_notes or 'Patient outcome requires this procedure.'}

Per CMS LCD L35041 (Section 4.2), this procedure is covered when conservative treatments have failed, which is documented in the attached clinical notes.

Please review the attached records and reprocess this claim for payment.

Sincerely,
{claim.provider_name}
"""
        return self._build_appeal_response(claim, mock_text, ["Documentation of prior failed physical therapy."], [], 65, "clinical")
