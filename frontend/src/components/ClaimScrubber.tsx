import React, { useState } from 'react';
import { v2api, type ScrubResult } from '../lib/v2api';

export function ClaimScrubber() {
  const [cptCodes, setCptCodes] = useState('99214, 27447');
  const [icd10Codes, setIcd10Codes] = useState('M17.11, I10');
  const [payer, setPayer] = useState('UHC');
  const [hasPriorAuth, setHasPriorAuth] = useState(false);
  const [dos, setDos] = useState('2024-06-15');
  const [result, setResult] = useState<ScrubResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleScrub = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await v2api.scrubClaim({
        cpt_codes: cptCodes.split(',').map(s => s.trim()).filter(Boolean),
        icd10_codes: icd10Codes.split(',').map(s => s.trim()).filter(Boolean),
        payer,
        has_prior_auth: hasPriorAuth,
        date_of_service: dos,
      });
      setResult(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const statusBadge = (status: string) => {
    const colors: Record<string, string> = {
      pass: 'bg-green-100 text-green-800',
      warn: 'bg-yellow-100 text-yellow-800',
      reject: 'bg-red-100 text-red-800',
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  const severityBadge = (severity: string) => {
    const colors: Record<string, string> = {
      reject: 'bg-red-100 text-red-700',
      warn: 'bg-yellow-100 text-yellow-700',
      info: 'bg-blue-100 text-blue-700',
    };
    return colors[severity] || 'bg-gray-100 text-gray-700';
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Claim Scrubber</h2>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">CPT Codes (comma-separated)</label>
          <input
            type="text" value={cptCodes} onChange={e => setCptCodes(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">ICD-10 Codes (comma-separated)</label>
          <input
            type="text" value={icd10Codes} onChange={e => setIcd10Codes(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Payer</label>
          <select
            value={payer} onChange={e => setPayer(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
          >
            <option value="UHC">UnitedHealthcare</option>
            <option value="Aetna">Aetna</option>
            <option value="BCBS">Blue Cross Blue Shield</option>
            <option value="Medicare">Medicare</option>
            <option value="Medicaid">Medicaid</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Date of Service</label>
          <input
            type="date" value={dos} onChange={e => setDos(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div className="flex items-center gap-2 pt-6">
          <input
            type="checkbox" checked={hasPriorAuth} onChange={e => setHasPriorAuth(e.target.checked)}
            className="rounded border-gray-300"
          />
          <label className="text-sm text-gray-700">Prior Authorization Obtained</label>
        </div>
      </div>

      <button
        onClick={handleScrub} disabled={loading}
        className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50"
      >
        {loading ? 'Scrubbing...' : 'Scrub Claim'}
      </button>

      {error && <div className="mt-4 p-3 bg-red-50 text-red-700 text-sm rounded-lg">{error}</div>}

      {result && (
        <div className="mt-6 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className={`px-3 py-1 rounded-full text-sm font-bold ${statusBadge(result.status)}`}>
                {result.status.toUpperCase()}
              </span>
              <span className="text-sm text-gray-500">{result.payer_rules_checked} rules checked</span>
            </div>
            <span className="text-sm text-gray-500">
              Confidence: {Math.round(result.confidence * 100)}%
            </span>
          </div>

          {result.issues.length > 0 ? (
            <div className="space-y-2">
              {result.issues.map((issue, i) => (
                <div key={i} className="p-3 border border-gray-200 rounded-lg">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${severityBadge(issue.severity)}`}>
                      {issue.severity}
                    </span>
                    <span className="text-xs font-mono text-gray-400">{issue.code}</span>
                  </div>
                  <p className="text-sm text-gray-900">{issue.message}</p>
                  {issue.suggestion && (
                    <p className="text-xs text-blue-600 mt-1">Fix: {issue.suggestion}</p>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="p-4 bg-green-50 rounded-lg text-green-700 text-sm">
              No issues found. Claim is ready for submission.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
