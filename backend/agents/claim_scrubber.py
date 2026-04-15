"""Claim Scrubber Agent — validates claims before submission."""

from __future__ import annotations

from backend.models.pipeline import ScrubResult, ScrubIssue
from backend.rules.cpt_icd_map import (
    check_medical_necessity,
    is_em_code,
    is_surgical_code,
    needs_modifier_25,
    load_cpt_codes,
    load_icd10_codes,
)
from backend.rules.payer_rules import check_payer_rules


class ClaimScrubber:
    """Pre-submission claim validation against coding rules and payer policies."""

    async def scrub(
        self,
        cpt_codes: list[str],
        icd10_codes: list[str],
        payer: str,
        modifiers: dict[str, str] | None = None,
        date_of_service: str = "",
        has_prior_auth: bool = False,
    ) -> ScrubResult:
        """
        Validate a claim and return scrub results.

        Args:
            cpt_codes: List of CPT codes on the claim.
            icd10_codes: List of ICD-10 diagnosis codes.
            payer: Payer short name (UHC, Aetna, BCBS, Medicare, Medicaid).
            modifiers: Dict of CPT code -> modifier (e.g., {"99214": "-25"}).
            date_of_service: Date of service in YYYY-MM-DD format.
            has_prior_auth: Whether prior authorization was obtained.
        """
        if modifiers is None:
            modifiers = {}

        issues: list[ScrubIssue] = []
        known_cpts = load_cpt_codes()
        known_icds = load_icd10_codes()

        # 1. Validate CPT codes exist
        for code in cpt_codes:
            if code not in known_cpts:
                issues.append(ScrubIssue(
                    severity="warn",
                    code="scrub-cpt-unknown",
                    message=f"CPT code {code} not found in reference data.",
                    suggestion="Verify the CPT code is correct and current.",
                ))

        # 2. Validate ICD-10 codes exist
        for code in icd10_codes:
            if code not in known_icds:
                issues.append(ScrubIssue(
                    severity="warn",
                    code="scrub-icd-unknown",
                    message=f"ICD-10 code {code} not found in reference data.",
                    suggestion="Verify the ICD-10 code is correct and current.",
                ))

        # 3. Check medical necessity (CPT-ICD linkage)
        for cpt in cpt_codes:
            if not check_medical_necessity(cpt, icd10_codes):
                issues.append(ScrubIssue(
                    severity="reject",
                    code="scrub-med-necessity",
                    message=f"CPT {cpt} lacks supporting medical necessity diagnosis.",
                    suggestion=f"Add an appropriate ICD-10 code that supports CPT {cpt}.",
                ))

        # 4. Check modifier -25 requirement
        has_same_day_procedure = needs_modifier_25(cpt_codes)
        has_mod_25 = any(m == "-25" for m in modifiers.values())
        if has_same_day_procedure and not has_mod_25:
            em_codes = [c for c in cpt_codes if is_em_code(c)]
            for em in em_codes:
                issues.append(ScrubIssue(
                    severity="reject",
                    code="scrub-mod25",
                    message=f"E&M code {em} requires modifier -25 for same-day procedure.",
                    suggestion="Add modifier -25 to the E&M code.",
                ))

        # 5. Check for missing diagnosis codes
        if not icd10_codes:
            issues.append(ScrubIssue(
                severity="reject",
                code="scrub-no-dx",
                message="No diagnosis codes on claim.",
                suggestion="Add at least one ICD-10 diagnosis code.",
            ))

        # 6. Check for missing CPT codes
        if not cpt_codes:
            issues.append(ScrubIssue(
                severity="reject",
                code="scrub-no-cpt",
                message="No procedure codes on claim.",
                suggestion="Add at least one CPT procedure code.",
            ))

        # 7. Run payer-specific rules
        payer_issues = check_payer_rules(
            payer=payer,
            cpt_codes=cpt_codes,
            icd10_codes=icd10_codes,
            date_of_service=date_of_service,
            has_prior_auth=has_prior_auth,
            has_modifier_25=has_mod_25,
            has_same_day_procedure=has_same_day_procedure,
        )
        issues.extend(payer_issues)

        # Determine overall status
        has_reject = any(i.severity == "reject" for i in issues)
        has_warn = any(i.severity == "warn" for i in issues)

        if has_reject:
            status = "reject"
        elif has_warn:
            status = "warn"
        else:
            status = "pass"

        # Calculate confidence
        total_checks = 7 + len(payer_issues)
        passing_checks = total_checks - len(issues)
        confidence = max(0.0, min(1.0, passing_checks / max(total_checks, 1)))

        return ScrubResult(
            status=status,
            issues=issues,
            payer_rules_checked=len(payer_issues) + 7,
            confidence=confidence,
        )
