"""Payer-specific validation rules engine."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta
from functools import lru_cache

from backend.models.pipeline import ScrubIssue

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")


@lru_cache(maxsize=1)
def load_payer_rules() -> dict:
    path = os.path.join(DATA_DIR, "payer_rules.json")
    with open(path, "r") as f:
        return json.load(f)


def get_payer_config(payer: str) -> dict | None:
    """Look up payer config by short name (UHC, Aetna, BCBS, Medicare, Medicaid)."""
    rules = load_payer_rules()
    return rules.get(payer)


def get_timely_filing_days(payer: str) -> int:
    cfg = get_payer_config(payer)
    if cfg:
        return cfg.get("timely_filing_days", 365)
    return 365


def _matches_cpt_pattern(cpt_code: str, pattern: str) -> bool:
    """Check if a CPT code matches a payer rule pattern (supports * wildcard)."""
    if pattern == "*":
        return True
    regex = pattern.replace("*", ".*")
    return bool(re.match(regex, cpt_code))


def check_payer_rules(
    payer: str,
    cpt_codes: list[str],
    icd10_codes: list[str],
    date_of_service: str = "",
    has_prior_auth: bool = False,
    has_modifier_25: bool = False,
    has_same_day_procedure: bool = False,
) -> list[ScrubIssue]:
    """
    Run payer-specific rules against a claim and return any issues found.
    """
    cfg = get_payer_config(payer)
    if not cfg:
        return []

    issues: list[ScrubIssue] = []
    rules = cfg.get("rules", [])

    for rule in rules:
        rule_id = rule["id"]
        description = rule["description"]
        severity = rule.get("severity", "warn")
        condition = rule.get("condition", "")

        # Determine which CPT codes this rule applies to
        applicable_cpts = []
        if "cpt_codes" in rule:
            applicable_cpts = [c for c in cpt_codes if c in rule["cpt_codes"]]
        elif "cpt_pattern" in rule:
            applicable_cpts = [c for c in cpt_codes if _matches_cpt_pattern(c, rule["cpt_pattern"])]

        if not applicable_cpts:
            continue

        # Evaluate conditions
        triggered = False

        if condition == "same_day_procedure" and has_same_day_procedure and not has_modifier_25:
            triggered = True
        elif condition == "no_prior_auth" and not has_prior_auth:
            triggered = True
        elif condition in ("duplicate_30_days", "duplicate_45_days", "duplicate_60_days"):
            # Duplicate detection would require claim history; skip in scrubbing
            pass
        elif condition == "no_conservative_therapy":
            # Would need clinical note analysis; flag as warning
            triggered = False  # Cannot determine from claim data alone
        elif condition == "insufficient_documentation":
            pass  # Cannot determine from claim data alone
        elif condition == "pos_mismatch":
            pass  # Would need POS validation logic
        elif condition == "no_medical_necessity":
            from backend.rules.cpt_icd_map import check_medical_necessity
            for cpt in applicable_cpts:
                if not check_medical_necessity(cpt, icd10_codes):
                    triggered = True
                    break

        if triggered:
            suggestion = ""
            if condition == "no_prior_auth":
                suggestion = "Obtain prior authorization before resubmitting."
            elif condition == "same_day_procedure":
                suggestion = "Add modifier -25 to the E&M code."
            elif condition == "no_medical_necessity":
                from backend.rules.cpt_icd_map import suggest_icd10_for_cpt
                for cpt in applicable_cpts:
                    suggested = suggest_icd10_for_cpt(cpt)
                    if suggested:
                        suggestion = f"Consider adding one of: {', '.join(suggested)}"
                        break

            issues.append(ScrubIssue(
                severity=severity,
                code=rule_id,
                message=description,
                suggestion=suggestion,
            ))

    # Check timely filing
    if date_of_service:
        try:
            dos = datetime.strptime(date_of_service, "%Y-%m-%d")
            filing_limit = dos + timedelta(days=get_timely_filing_days(payer))
            if datetime.utcnow() > filing_limit:
                issues.append(ScrubIssue(
                    severity="reject",
                    code=f"{payer.lower()}-timely",
                    message=f"Claim exceeds {payer} timely filing limit of {get_timely_filing_days(payer)} days.",
                    suggestion="File a timely filing appeal with proof of original submission.",
                ))
        except ValueError:
            pass

    return issues
