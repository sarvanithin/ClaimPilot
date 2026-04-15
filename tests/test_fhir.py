"""Tests for the Mock FHIR server and seed data."""

import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


class TestFHIRSeedData:
    def test_load_patients(self):
        from backend.fhir.seed_data import get_all_patients
        patients = get_all_patients()
        assert len(patients) >= 20, "Should have at least 20 synthetic patients"

    def test_get_patient_by_id(self):
        from backend.fhir.seed_data import get_patient
        patient = get_patient("pat-001")
        assert patient is not None
        assert patient.id == "pat-001"
        assert patient.name[0].family == "Johnson"

    def test_patient_not_found(self):
        from backend.fhir.seed_data import get_patient
        assert get_patient("nonexistent") is None

    def test_load_encounters(self):
        from backend.fhir.seed_data import get_all_encounters
        encounters = get_all_encounters()
        assert len(encounters) >= 20, "Should have at least 20 encounters"

    def test_get_patient_encounters(self):
        from backend.fhir.seed_data import get_patient_encounters
        encounters = get_patient_encounters("pat-001")
        assert len(encounters) >= 2, "Patient 001 should have multiple encounters"

    def test_load_coverages(self):
        from backend.fhir.seed_data import get_all_coverages
        coverages = get_all_coverages()
        assert len(coverages) >= 20

    def test_get_patient_coverage(self):
        from backend.fhir.seed_data import get_patient_coverage
        coverage = get_patient_coverage("pat-001")
        assert coverage is not None
        assert coverage.payer == "UHC"


class TestFHIREndpoints:
    def test_list_patients(self):
        resp = client.get("/fhir/Patient")
        assert resp.status_code == 200
        data = resp.json()
        assert data["resourceType"] == "Bundle"
        assert data["total"] >= 20

    def test_read_patient(self):
        resp = client.get("/fhir/Patient/pat-001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["resourceType"] == "Patient"
        assert data["id"] == "pat-001"

    def test_read_patient_not_found(self):
        resp = client.get("/fhir/Patient/nonexistent")
        assert resp.status_code == 404

    def test_patient_encounters(self):
        resp = client.get("/fhir/Patient/pat-001/Encounter")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 2

    def test_read_encounter(self):
        resp = client.get("/fhir/Encounter/enc-001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["resourceType"] == "Encounter"

    def test_list_coverages(self):
        resp = client.get("/fhir/Coverage")
        assert resp.status_code == 200

    def test_read_coverage(self):
        resp = client.get("/fhir/Coverage/cov-001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["payer"] == "UHC"

    def test_create_and_read_claim(self):
        claim = {
            "resourceType": "Claim",
            "patient_id": "pat-001",
            "status": "active",
        }
        resp = client.post("/fhir/Claim", json=claim)
        assert resp.status_code == 200
        claim_id = resp.json()["id"]

        resp2 = client.get(f"/fhir/Claim/{claim_id}")
        assert resp2.status_code == 200
