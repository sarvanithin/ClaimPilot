"""Tests for the pipeline submission and denial flow."""

import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


class TestV2Endpoints:
    def test_list_patients(self):
        resp = client.get("/api/v2/fhir/patients")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 20

    def test_patient_encounters(self):
        resp = client.get("/api/v2/fhir/patients/pat-001/encounters")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 2

    def test_charge_capture(self):
        resp = client.post("/api/v2/charges/capture", json={
            "encounter_id": "enc-001",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["cpt_codes"]) > 0
        assert len(data["icd10_codes"]) > 0
        assert data["total_estimated_charge"] > 0

    def test_claim_scrub(self):
        resp = client.post("/api/v2/claims/scrub", json={
            "cpt_codes": ["99214", "27447"],
            "icd10_codes": ["M17.11"],
            "payer": "UHC",
            "has_prior_auth": True,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("pass", "warn", "reject")

    def test_submit_claim(self):
        resp = client.post("/api/v2/claims/submit", json={
            "encounter_id": "enc-001",
            "patient_id": "pat-001",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "claim_id" in data
        assert data["status"] == "submitted"
        return data["claim_id"]

    def test_full_pipeline_flow(self):
        # Submit
        resp = client.post("/api/v2/claims/submit", json={
            "encounter_id": "enc-004",
            "patient_id": "pat-002",
        })
        assert resp.status_code == 200
        claim_id = resp.json()["claim_id"]

        # Check pipeline
        resp = client.get("/api/v2/pipeline")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

        # Deny
        resp = client.post(f"/api/v2/claims/{claim_id}/deny", json={
            "carc_code": "CO-50",
        })
        assert resp.status_code == 200
        assert resp.json()["carc_code"] == "CO-50"

        # Appeal
        resp = client.post(f"/api/v2/claims/{claim_id}/appeal")
        assert resp.status_code == 200
        data = resp.json()
        assert data["appeal_generated"] is True
        assert len(data["appeal_text"]) > 100

    def test_pipeline_stats(self):
        # Submit a claim first to ensure data exists
        client.post("/api/v2/claims/submit", json={
            "encounter_id": "enc-006",
            "patient_id": "pat-003",
        })
        resp = client.get("/api/v2/pipeline/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_claims"] >= 1

    def test_denial_codes_list(self):
        resp = client.get("/api/v2/denial-codes")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0
        assert any(d["code"] == "CO-50" for d in data)
