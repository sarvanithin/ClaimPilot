import React, { useState, useEffect, useCallback } from 'react';
import { v2api, type PipelineItem, type PipelineStats } from '../lib/v2api';

const STATUS_COLUMNS = [
  { key: 'captured', label: 'Captured', color: 'bg-gray-100 text-gray-800' },
  { key: 'scrubbed', label: 'Scrubbed', color: 'bg-blue-100 text-blue-800' },
  { key: 'submitted', label: 'Submitted', color: 'bg-indigo-100 text-indigo-800' },
  { key: 'pending', label: 'Pending', color: 'bg-yellow-100 text-yellow-800' },
  { key: 'paid', label: 'Paid', color: 'bg-green-100 text-green-800' },
  { key: 'denied', label: 'Denied', color: 'bg-red-100 text-red-800' },
  { key: 'appealed', label: 'Appealed', color: 'bg-orange-100 text-orange-800' },
  { key: 'resolved', label: 'Resolved', color: 'bg-emerald-100 text-emerald-800' },
];

export function ClaimsPipeline() {
  const [items, setItems] = useState<PipelineItem[]>([]);
  const [stats, setStats] = useState<PipelineStats | null>(null);
  const [selectedItem, setSelectedItem] = useState<PipelineItem | null>(null);
  const [denyCode, setDenyCode] = useState('CO-50');
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [pipeline, pipelineStats] = await Promise.all([
        v2api.getPipeline(),
        v2api.getPipelineStats(),
      ]);
      setItems(pipeline.items);
      setStats(pipelineStats);
    } catch (err) {
      console.error('Failed to load pipeline:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const handleDeny = async (claimId: string) => {
    setActionLoading(true);
    try {
      await v2api.denyClaim(claimId, denyCode);
      await refresh();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleAppeal = async (claimId: string) => {
    setActionLoading(true);
    try {
      const result = await v2api.appealClaim(claimId);
      await refresh();
      const updated = items.find(i => i.id === claimId);
      if (updated) setSelectedItem({ ...updated, appeal_text: result.appeal_text, status: 'appealed' });
    } catch (err: any) {
      alert(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const getColumnItems = (status: string) => items.filter(i => i.status === status);

  return (
    <div className="space-y-6">
      {/* Stats bar */}
      {stats && stats.total_claims > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-sm">
            <div>
              <span className="text-gray-500">Total Claims</span>
              <p className="text-xl font-bold text-gray-900">{stats.total_claims}</p>
            </div>
            <div>
              <span className="text-gray-500">Total Charges</span>
              <p className="text-xl font-bold text-gray-900">${stats.total_charges.toLocaleString('en-US', { maximumFractionDigits: 0 })}</p>
            </div>
            <div>
              <span className="text-gray-500">Total Paid</span>
              <p className="text-xl font-bold text-green-600">${stats.total_paid.toLocaleString('en-US', { maximumFractionDigits: 0 })}</p>
            </div>
            <div>
              <span className="text-gray-500">Total Denied</span>
              <p className="text-xl font-bold text-red-600">${stats.total_denied.toLocaleString('en-US', { maximumFractionDigits: 0 })}</p>
            </div>
            <div>
              <span className="text-gray-500">Denial Rate</span>
              <p className="text-xl font-bold text-orange-600">{(stats.denial_rate * 100).toFixed(1)}%</p>
            </div>
          </div>
        </div>
      )}

      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">Claims Pipeline</h2>
        <button
          onClick={refresh}
          disabled={loading}
          className="px-3 py-1 text-sm text-blue-600 hover:text-blue-800 font-medium"
        >
          {loading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {items.length === 0 ? (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-12 text-center">
          <p className="text-gray-500">No claims in pipeline. Submit claims from the EHR Viewer to see them here.</p>
        </div>
      ) : (
        <div className="flex gap-3 overflow-x-auto pb-4">
          {STATUS_COLUMNS.map(col => {
            const colItems = getColumnItems(col.key);
            return (
              <div key={col.key} className="flex-shrink-0 w-64">
                <div className="flex items-center gap-2 mb-2">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${col.color}`}>{col.label}</span>
                  <span className="text-xs text-gray-400">{colItems.length}</span>
                </div>
                <div className="space-y-2">
                  {colItems.map(item => (
                    <div
                      key={item.id}
                      className={`bg-white rounded-lg border p-3 cursor-pointer hover:shadow-md transition ${
                        selectedItem?.id === item.id ? 'border-blue-400 shadow-md' : 'border-gray-200'
                      }`}
                      onClick={() => setSelectedItem(item)}
                    >
                      <div className="text-xs font-mono text-gray-400 mb-1">{item.id}</div>
                      <div className="text-sm font-medium text-gray-900 truncate">{item.patient_name}</div>
                      <div className="text-xs text-gray-500 mt-1">{item.cpt_codes.join(', ')}</div>
                      <div className="flex items-center justify-between mt-2">
                        <span className="text-xs text-gray-500">{item.payer_name}</span>
                        <span className="text-sm font-bold text-gray-700">
                          ${item.total_charge.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                        </span>
                      </div>
                      {item.denial_code && (
                        <div className="mt-1 text-xs text-red-600 font-medium">{item.denial_code}</div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Detail panel */}
      {selectedItem && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Claim: {selectedItem.id}</h3>
            <button onClick={() => setSelectedItem(null)} className="text-gray-400 hover:text-gray-600 text-sm">Close</button>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm mb-4">
            <div><span className="text-gray-500">Patient:</span> <span className="font-medium">{selectedItem.patient_name}</span></div>
            <div><span className="text-gray-500">Payer:</span> <span className="font-medium">{selectedItem.payer_name}</span></div>
            <div><span className="text-gray-500">Charge:</span> <span className="font-medium">${selectedItem.total_charge.toLocaleString()}</span></div>
            <div><span className="text-gray-500">CPT:</span> <span className="font-mono">{selectedItem.cpt_codes.join(', ')}</span></div>
            <div><span className="text-gray-500">ICD-10:</span> <span className="font-mono">{selectedItem.icd10_codes.join(', ')}</span></div>
            <div><span className="text-gray-500">DOS:</span> <span className="font-medium">{selectedItem.date_of_service}</span></div>
          </div>

          {selectedItem.denial_code && (
            <div className="p-3 bg-red-50 rounded-lg mb-4">
              <p className="text-sm font-medium text-red-800">Denial: {selectedItem.denial_code}</p>
              <p className="text-sm text-red-600">{selectedItem.denial_reason}</p>
            </div>
          )}

          {selectedItem.appeal_text && (
            <div className="p-3 bg-blue-50 rounded-lg mb-4">
              <p className="text-sm font-medium text-blue-800 mb-2">Appeal Letter</p>
              <pre className="text-xs text-blue-900 whitespace-pre-wrap">{selectedItem.appeal_text}</pre>
            </div>
          )}

          <div className="flex gap-2 mt-4">
            {selectedItem.status === 'submitted' && (
              <>
                <select value={denyCode} onChange={e => setDenyCode(e.target.value)} className="px-2 py-1 text-sm border rounded">
                  <option value="CO-50">CO-50 (Medical Necessity)</option>
                  <option value="CO-197">CO-197 (No Prior Auth)</option>
                  <option value="CO-4">CO-4 (Modifier Error)</option>
                  <option value="CO-11">CO-11 (Dx/Proc Mismatch)</option>
                  <option value="CO-29">CO-29 (Timely Filing)</option>
                  <option value="CO-18">CO-18 (Duplicate)</option>
                </select>
                <button
                  onClick={() => handleDeny(selectedItem.id)}
                  disabled={actionLoading}
                  className="px-3 py-1 text-sm font-medium text-white bg-red-600 rounded hover:bg-red-700 disabled:opacity-50"
                >
                  Simulate Denial
                </button>
              </>
            )}
            {selectedItem.status === 'denied' && (
              <button
                onClick={() => handleAppeal(selectedItem.id)}
                disabled={actionLoading}
                className="px-3 py-1 text-sm font-medium text-white bg-orange-600 rounded hover:bg-orange-700 disabled:opacity-50"
              >
                Generate Appeal
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
