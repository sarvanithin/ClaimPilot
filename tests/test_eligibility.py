"""Tests for the Eligibility Verification Agent."""

import pytest
from backend.agents.eligibility import EligibilityAgent


@pytest.fixture
def agent():
    return EligibilityAgent()


class TestEligibilityAgent:
    @pytest.mark.asyncio
    async def test_eligible_patient(self, agent):
        result = await agent.verify("pat-001", "2024-06-15")
        assert result.eligible is True
        assert result.payer == "UHC"
        assert result.member_id != ""
        assert result.coverage_active is True

    @pytest.mark.asyncio
    async def test_patient_not_found(self, agent):
        result = await agent.verify("nonexistent")
        assert result.eligible is False
        assert "Patient not found" in result.issues[0]

    @pytest.mark.asyncio
    async def test_deductible_info(self, agent):
        result = await agent.verify("pat-001")
        assert result.deductible > 0
        assert result.deductible_remaining >= 0

    @pytest.mark.asyncio
    async def test_medicare_patient(self, agent):
        result = await agent.verify("pat-007")
        assert result.eligible is True
        assert result.payer == "Medicare"

    @pytest.mark.asyncio
    async def test_medicaid_patient(self, agent):
        result = await agent.verify("pat-009")
        assert result.eligible is True
        assert result.payer == "Medicaid"
        assert result.copay == 0

    @pytest.mark.asyncio
    async def test_date_outside_coverage(self, agent):
        result = await agent.verify("pat-001", "2025-06-15")
        assert result.eligible is False
        assert any("outside coverage" in i for i in result.issues)

    @pytest.mark.asyncio
    async def test_eligibility_api_endpoint(self):
        from fastapi.testclient import TestClient
        from backend.main import app
        client = TestClient(app)
        resp = client.post("/api/v2/eligibility/verify", json={
            "patient_id": "pat-001",
            "date_of_service": "2024-06-15",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["eligible"] is True
