import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

export const apiClient = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

export interface Claim {
    patient_id: string;
    procedure_code: string;
    diagnosis_codes: string[];
    payer: string;
    denial_code: string;
    denial_reason: string;
    date_of_service: string;
    provider_name: string;
    clinical_notes?: string;
}

export interface PolicyReference {
    source: string;
    section: string;
    text: string;
    relevance: string;
}

export interface DenialAnalysis {
    denial_category: string;
    denial_code: string;
    denial_description: string;
    root_cause: string;
    appeal_strategy: string;
    success_probability: string;
}

export interface AppealLetter {
    subject_line: string;
    date: string;
    payer_address: string;
    re_line: string;
    opening: string;
    medical_necessity: string;
    policy_citations: string;
    conclusion: string;
    attachments_needed: string[];
    full_text: string;
}

export interface AppealResult {
    analysis: DenialAnalysis;
    policies: PolicyReference[];
    appeal: AppealLetter;
}

export const analyzeClaim = async (claim: Claim): Promise<AppealResult> => {
    const response = await apiClient.post<AppealResult>('/claims/analyze', claim);
    return response.data;
};

export const getDemoClaims = async () => {
    const response = await apiClient.get('/demo-claims');
    return response.data;
};
