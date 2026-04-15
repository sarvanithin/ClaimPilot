import React, { useState } from 'react';
import { v2api, type ChargeCaptureResult } from '../lib/v2api';

interface ChargeCaptureProps {
  encounterId?: string;
  onResult?: (result: ChargeCaptureResult) => void;
}

export function ChargeCapture({ encounterId, onResult }: ChargeCaptureProps) {
  const [inputId, setInputId] = useState(encounterId || '');
  const [result, setResult] = useState<ChargeCaptureResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleCapture = async () => {
    const id = inputId.trim();
    if (!id) return;
    setLoading(true);
    setError('');
    try {
      const data = await v2api.captureCharges(id);
      setResult(data);
      onResult?.(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const confidenceColor = (c: number) => {
    if (c >= 0.9) return 'text-green-700 bg-green-100';
    if (c >= 0.7) return 'text-yellow-700 bg-yellow-100';
    return 'text-red-700 bg-red-100';
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Charge Capture</h2>

      <div className="flex gap-3 mb-6">
        <input
          type="text"
          value={inputId}
          onChange={e => setInputId(e.target.value)}
          placeholder="Encounter ID (e.g., enc-001)"
          className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
        <button
          onClick={handleCapture}
          disabled={loading || !inputId.trim()}
          className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? 'Capturing...' : 'Capture Charges'}
        </button>
      </div>

      {error && <div className="mb-4 p-3 bg-red-50 text-red-700 text-sm rounded-lg">{error}</div>}

      {result && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-500">Encounter: {result.encounter_id}</span>
            <span className="text-lg font-bold text-gray-900">
              Total: ${result.total_estimated_charge.toLocaleString('en-US', { minimumFractionDigits: 2 })}
            </span>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-2">CPT Codes ({result.cpt_codes.length})</h3>
            <div className="space-y-2">
              {result.cpt_codes.map((cpt, i) => (
                <div key={i} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center gap-3">
                    <span className="font-mono font-bold text-blue-700">{cpt.code}</span>
                    {cpt.modifier && (
                      <span className="px-1.5 py-0.5 text-xs font-medium bg-orange-100 text-orange-700 rounded">
                        {cpt.modifier}
                      </span>
                    )}
                    <span className="text-sm text-gray-600">{cpt.description}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${confidenceColor(cpt.confidence)}`}>
                      {Math.round(cpt.confidence * 100)}%
                    </span>
                    <span className="text-sm font-medium text-gray-900">
                      ${cpt.charge.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-2">ICD-10 Codes ({result.icd10_codes.length})</h3>
            <div className="space-y-2">
              {result.icd10_codes.map((icd, i) => (
                <div key={i} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center gap-3">
                    <span className="font-mono font-bold text-purple-700">{icd.code}</span>
                    <span className="text-sm text-gray-600">{icd.description}</span>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${confidenceColor(icd.confidence)}`}>
                    {Math.round(icd.confidence * 100)}%
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="text-sm text-gray-500">
            Place of Service: <span className="font-medium">{result.place_of_service}</span>
          </div>
        </div>
      )}
    </div>
  );
}
