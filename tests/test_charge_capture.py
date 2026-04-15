"""Tests for the Charge Capture Agent."""

import pytest
from backend.agents.charge_capture import ChargeCaptureAgent


@pytest.fixture
def agent():
    return ChargeCaptureAgent()


class TestChargeCaptureAgent:
    @pytest.mark.asyncio
    async def test_capture_knee_replacement(self, agent):
        note = """Patient is a 65-year-old male with worsening right knee pain.
        Failed conservative treatment including physical therapy.
        X-ray shows Kellgren-Lawrence Grade IV osteoarthritis.
        Recommend total knee arthroplasty. Prior auth to be submitted to UHC."""
        result = await agent.capture("enc-001", note, "Office Visit")
        cpt_codes = [c.code for c in result.cpt_codes]
        assert "27447" in cpt_codes, "Should capture TKA CPT code"
        icd_codes = [c.code for c in result.icd10_codes]
        assert any("M17" in c for c in icd_codes) or any("osteoarthritis" in c.description.lower() for c in result.icd10_codes), \
            "Should capture knee OA diagnosis"
        assert result.total_estimated_charge > 0

    @pytest.mark.asyncio
    async def test_capture_cholecystectomy(self, agent):
        note = """Patient with recurrent RUQ pain. US showed gallstones.
        Recommend laparoscopic cholecystectomy with cholangiography."""
        result = await agent.capture("enc-004", note, "Surgical Day Case")
        cpt_codes = [c.code for c in result.cpt_codes]
        assert "47562" in cpt_codes or "47563" in cpt_codes

    @pytest.mark.asyncio
    async def test_capture_ed_visit(self, agent):
        note = """53-year-old male with COPD presents with acute dyspnea.
        SpO2 88% on RA. CXR: hyperinflation. Admitted for COPD exacerbation."""
        result = await agent.capture("enc-017", note, "ED Visit")
        cpt_codes = [c.code for c in result.cpt_codes]
        # Should have an ED E&M code
        assert any(c.startswith("9928") for c in cpt_codes), "Should capture ED E&M code"
        icd_codes = [c.code for c in result.icd10_codes]
        assert any("J44" in c for c in icd_codes), "Should capture COPD diagnosis"

    @pytest.mark.asyncio
    async def test_capture_psychotherapy(self, agent):
        note = """60-minute individual psychotherapy session. CBT focus.
        Patient with major depressive disorder and generalized anxiety."""
        result = await agent.capture("enc-013", note, "Psychotherapy Session")
        cpt_codes = [c.code for c in result.cpt_codes]
        assert "90837" in cpt_codes, "Should capture 60-min psychotherapy code"

    @pytest.mark.asyncio
    async def test_modifier_25_applied(self, agent):
        note = """Office visit for established patient with knee osteoarthritis.
        Performed arthrocentesis of right knee joint during the visit."""
        result = await agent.capture("test-mod", note, "Office Visit")
        em_codes = [c for c in result.cpt_codes if c.code.startswith("992")]
        if em_codes:
            assert em_codes[0].modifier == "-25", "E&M should have modifier -25 with same-day procedure"

    @pytest.mark.asyncio
    async def test_capture_empty_note(self, agent):
        result = await agent.capture("test-empty", "", "Office Visit")
        # Should at least assign a basic E&M code
        assert len(result.cpt_codes) >= 1

    @pytest.mark.asyncio
    async def test_place_of_service_detection(self, agent):
        note = """Patient admitted to hospital for acute care."""
        result = await agent.capture("test-pos", note, "Hospital Admission")
        assert result.place_of_service in ("21", "23"), "Should detect inpatient/hospital POS"
