import json
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from backend.models.claim import Claim, DenialAnalysis
from backend.agent.prompts import DENIAL_CLASSIFICATION_PROMPT
from backend.config import settings
import os

class DenialClassifier:
    def __init__(self):
        self.llm = ChatGroq(
            model=settings.DEFAULT_MODEL,
            temperature=0.0,
            max_tokens=200, # optimizing tokens here
            api_key=settings.GROQ_API_KEY if settings.GROQ_API_KEY else "dummy_key",
            model_kwargs={"response_format": {"type": "json_object"}}
        )
        self.prompt = PromptTemplate(
            input_variables=["procedure_code", "diagnosis_codes", "denial_code", "denial_reason"],
            template=DENIAL_CLASSIFICATION_PROMPT
        )
        
    def classify(self, claim: Claim) -> DenialAnalysis:
        """Classifies the denial reason and produces an analysis"""
        # Note: If no API key is provided, we return a mock response for demonstration
        if not settings.GROQ_API_KEY:
            return self._mock_classify(claim)

        chain = self.prompt | self.llm
        response = chain.invoke({
            "procedure_code": claim.procedure_code,
            "diagnosis_codes": ", ".join(claim.diagnosis_codes),
            "denial_code": claim.denial_code,
            "denial_reason": claim.denial_reason
        })
        
        try:
            result = json.loads(response.content)
            
            return DenialAnalysis(
                track=result.get("track", "clinical"),
                denial_category=result.get("category", "unknown"),
                denial_code=claim.denial_code,
                denial_description=claim.denial_reason,
                root_cause=result.get("reasoning", ""),
                appeal_strategy="Cite relevant policy and demonstrate medical necessity." if result.get("track", "clinical") == "clinical" else "Provide administrative proof such as corrected claims or prior authorization records.",
                relevant_policies=[],
                success_probability="high" if result.get("confidence", 0) > 0.8 else "medium"
            )
        except Exception as e:
            print(f"Error parsing LLM response: {e}")
            return self._mock_classify(claim)
            
    def _mock_classify(self, claim: Claim) -> DenialAnalysis:
        """Fallback mock for UI testing when LLM isn't configured"""
        return DenialAnalysis(
            track="clinical",
            denial_category="medical_necessity",
            denial_code=claim.denial_code,
            denial_description="Not deemed a medical necessity by payer.",
            root_cause="Payer requires documentation of failed conservative treatment.",
            appeal_strategy="Cite relevant policy and demonstrate medical necessity through clinical notes.",
            relevant_policies=[],
            success_probability="high"
        )
