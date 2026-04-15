const API_BASE = (import.meta.env.VITE_API_URL || '/api') + '/v2';

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const resp = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!resp.ok) {
    const error = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new Error(error.detail || `HTTP ${resp.status}`);
  }
  return resp.json();
}

// Types

export interface PatientSummary {
  id: string;
  name: string;
  gender: string;
  birthDate: string;
  conditions: string[];
  payer: string;
  plan: string;
  member_id: string;
  encounter_count: number;
}

export interface EncounterSummary {
  id: string;
  date: string;
  type: string;
  provider: string;
  facility: string;
  status: string;
  clinical_note: string;
}

export interface CPTCodeResult {
  code: string;
  description: string;
  modifier: string;
  confidence: number;
  charge: number;
}

export interface ICD10CodeResult {
  code: string;
  description: string;
  confidence: number;
}

export interface ChargeCaptureResult {
  encounter_id: string;
  cpt_codes: CPTCodeResult[];
  icd10_codes: ICD10CodeResult[];
  place_of_service: string;
  total_estimated_charge: number;
}

export interface ScrubIssue {
  severity: string;
  code: string;
  message: string;
  suggestion: string;
}

export interface ScrubResult {
  status: string;
  issues: ScrubIssue[];
  payer_rules_checked: number;
  confidence: number;
}

export interface PipelineItem {
  id: string;
  patient_id: string;
  patient_name: string;
  encounter_id: string;
  status: string;
  cpt_codes: string[];
  icd10_codes: string[];
  total_charge: number;
  payer: string;
  payer_name: string;
  provider: string;
  facility: string;
  date_of_service: string;
  created_at: string;
  updated_at: string;
  scrub_result: ScrubResult | null;
  denial_code: string | null;
  denial_reason: string | null;
  appeal_id: string | null;
  appeal_text: string | null;
  paid_amount: number | null;
}

export interface PipelineStats {
  total_claims: number;
  by_status: Record<string, number>;
  total_charges: number;
  total_paid: number;
  total_denied: number;
  denial_rate: number;
  average_charge: number;
  top_denial_codes: { code: string; count: number; description: string }[];
}

export interface SubmitResult {
  claim_id: string;
  status: string;
  charge_capture: ChargeCaptureResult;
  scrub_result: ScrubResult;
  claim_837p: Record<string, unknown>;
  pipeline_item: PipelineItem;
}

export interface DenialDetail {
  claim_id: string;
  patient_id: string;
  patient_name: string;
  carc_code: string;
  carc_description: string;
  denial_reason: string;
  total_charge: number;
  paid_amount: number;
  cpt_codes: string[];
  icd10_codes: string[];
  encounter_id: string;
  clinical_note_excerpt: string;
  supporting_documentation: string[];
  appeal_generated: boolean;
  appeal_text: string;
}

// API calls

export const v2api = {
  async getPatients(): Promise<{ patients: PatientSummary[]; total: number }> {
    return fetchJSON(`${API_BASE}/fhir/patients`);
  },

  async getPatientEncounters(patientId: string): Promise<{ encounters: EncounterSummary[]; total: number }> {
    return fetchJSON(`${API_BASE}/fhir/patients/${patientId}/encounters`);
  },

  async captureCharges(encounterId: string): Promise<ChargeCaptureResult> {
    return fetchJSON(`${API_BASE}/charges/capture`, {
      method: 'POST',
      body: JSON.stringify({ encounter_id: encounterId }),
    });
  },

  async scrubClaim(data: {
    cpt_codes: string[];
    icd10_codes: string[];
    payer: string;
    modifiers?: Record<string, string>;
    date_of_service?: string;
    has_prior_auth?: boolean;
  }): Promise<ScrubResult> {
    return fetchJSON(`${API_BASE}/claims/scrub`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async submitClaim(encounterId: string, patientId: string): Promise<SubmitResult> {
    return fetchJSON(`${API_BASE}/claims/submit`, {
      method: 'POST',
      body: JSON.stringify({ encounter_id: encounterId, patient_id: patientId }),
    });
  },

  async denyClaim(claimId: string, carcCode: string = 'CO-50'): Promise<DenialDetail> {
    return fetchJSON(`${API_BASE}/claims/${claimId}/deny`, {
      method: 'POST',
      body: JSON.stringify({ carc_code: carcCode }),
    });
  },

  async appealClaim(claimId: string): Promise<DenialDetail> {
    return fetchJSON(`${API_BASE}/claims/${claimId}/appeal`, {
      method: 'POST',
    });
  },

  async getPipeline(): Promise<{ items: PipelineItem[]; total: number }> {
    return fetchJSON(`${API_BASE}/pipeline`);
  },

  async getPipelineStats(): Promise<PipelineStats> {
    return fetchJSON(`${API_BASE}/pipeline/stats`);
  },
};
