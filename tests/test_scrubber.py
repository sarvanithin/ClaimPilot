"""Tests for the Claim Scrubber Agent."""

import pytest
from backend.agents.claim_scrubber import ClaimScrubber


@pytest.fixture
def scrubber():
    return ClaimScrubber()


class TestClaimScrubber:
    @pytest.mark.asyncio
    async def test_clean_claim_passes(self, scrubber):
        result = await scrubber.scrub(
            cpt_codes=["99213"],
            icd10_codes=["E11.9", "I10"],
            payer="UHC",
            date_of_service="2026-04-01",
        )
        assert result.status in ("pass", "warn"), "Simple E&M with valid dx should pass or warn"

    @pytest.mark.asyncio
    async def test_missing_diagnosis(self, scrubber):
        result = await scrubber.scrub(
            cpt_codes=["99213"],
            icd10_codes=[],
            payer="UHC",
        )
        assert result.status == "reject"
        assert any("No diagnosis" in i.message for i in result.issues)

    @pytest.mark.asyncio
    async def test_missing_cpt(self, scrubber):
        result = await scrubber.scrub(
            cpt_codes=[],
            icd10_codes=["E11.9"],
            payer="UHC",
        )
        assert result.status == "reject"
        assert any("No procedure" in i.message for i in result.issues)

    @pytest.mark.asyncio
    async def test_medical_necessity_failure(self, scrubber):
        result = await scrubber.scrub(
            cpt_codes=["27447"],  # TKA
            icd10_codes=["E11.9"],  # Diabetes - not linked to TKA
            payer="UHC",
            has_prior_auth=True,
        )
        assert result.status == "reject"
        has_necessity_issue = any("medical necessity" in i.message.lower() for i in result.issues)
        assert has_necessity_issue, "Should flag medical necessity mismatch"

    @pytest.mark.asyncio
    async def test_modifier_25_required(self, scrubber):
        result = await scrubber.scrub(
            cpt_codes=["99214", "20610"],  # E&M + arthrocentesis
            icd10_codes=["M17.11"],
            payer="UHC",
        )
        has_mod25_issue = any("modifier" in i.message.lower() or "mod" in i.code.lower() for i in result.issues)
        assert has_mod25_issue, "Should flag missing modifier -25"

    @pytest.mark.asyncio
    async def test_modifier_25_present(self, scrubber):
        result = await scrubber.scrub(
            cpt_codes=["99214", "20610"],
            icd10_codes=["M17.11"],
            payer="UHC",
            modifiers={"99214": "-25"},
        )
        mod25_issues = [i for i in result.issues if "mod25" in i.code or "modifier" in i.message.lower()]
        # Should not have modifier-25 issue when it's provided
        assert not any(i.code == "scrub-mod25" for i in result.issues)

    @pytest.mark.asyncio
    async def test_prior_auth_required(self, scrubber):
        result = await scrubber.scrub(
            cpt_codes=["27447"],  # TKA requires prior auth at UHC
            icd10_codes=["M17.11"],
            payer="UHC",
            has_prior_auth=False,
        )
        has_auth_issue = any("prior auth" in i.message.lower() or "authorization" in i.message.lower() for i in result.issues)
        assert has_auth_issue, "Should flag missing prior auth for TKA at UHC"

    @pytest.mark.asyncio
    async def test_payer_rules_counted(self, scrubber):
        result = await scrubber.scrub(
            cpt_codes=["99213"],
            icd10_codes=["E11.9"],
            payer="UHC",
        )
        assert result.payer_rules_checked > 0

    @pytest.mark.asyncio
    async def test_unknown_payer(self, scrubber):
        result = await scrubber.scrub(
            cpt_codes=["99213"],
            icd10_codes=["E11.9"],
            payer="UnknownPayer",
        )
        # Should still work, just no payer-specific rules
        assert result.status in ("pass", "warn", "reject")
