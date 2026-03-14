from backend.models.claim import Claim, AppealResult
from backend.agent.classifier import DenialClassifier
from backend.agent.retriever import PolicyRetriever
from backend.agent.appeal_writer import AppealWriter

class ClaimPilotAgent:
    """
    Main orchestrator that processes a denied claim and generates an appeal.
    """
    def __init__(self):
        self.classifier = DenialClassifier()
        self.retriever = PolicyRetriever()
        self.writer = AppealWriter()
        
    def process_claim(self, claim: Claim) -> AppealResult:
        """
        Runs the full agent pipeline.
        This is synchronous but can easily be made async if needed.
        """
        print(f"Step 1: Classifying denial for claim {claim.patient_id}")
        analysis = self.classifier.classify(claim)
        
        if analysis.track == "clinical":
            print(f"Step 2: Retrieving policies for {analysis.denial_category}")
            policies = self.retriever.retrieve_policies(
                procedure_code=claim.procedure_code,
                diagnosis_codes=claim.diagnosis_codes,
                denial_category=analysis.denial_category,
                payer=claim.payer
            )
        else:
            print(f"Step 2: Administrative denial detected, skipping RAG policy retrieval.")
            policies = []
        
        print(f"Step 3 & 4: Generating and refining appeal letter")
        appeal = self.writer.write_appeal(claim, analysis, policies)
        
        return AppealResult(
            analysis=analysis,
            policies=policies,
            appeal=appeal
        )
