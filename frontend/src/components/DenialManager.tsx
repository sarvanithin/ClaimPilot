import React, { useState, useEffect } from 'react';
import { v2api, type PipelineItem } from '../lib/v2api';

export function DenialManager() {
  const [deniedItems, setDeniedItems] = useState<PipelineItem[]>([]);
  const [selectedItem, setSelectedItem] = useState<PipelineItem | null>(null);
  const [appealText, setAppealText] = useState('');
  const [loading, setLoading] = useState(false);
  const [appealLoading, setAppealLoading] = useState(false);

  useEffect(() => {
    loadDenials();
  }, []);

  const loadDenials = async () => {
    setLoading(true);
    try {
      const data = await v2api.getPipeline();
      const denied = data.items.filter(i => i.status === 'denied' || i.status === 'appealed');
      setDeniedItems(denied);
    } catch (err) {
      console.error('Failed to load denials:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAppeal = async (claimId: string) => {
    setAppealLoading(true);
    try {
      const result = await v2api.appealClaim(claimId);
      setAppealText(result.appeal_text);
      await loadDenials();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setAppealLoading(false);
    }
  };

  if (loading) return <div className="p-8 text-center text-gray-500">Loading denials...</div>;

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Denial Manager</h2>
          <button onClick={loadDenials} className="text-sm text-blue-600 hover:text-blue-800">Refresh</button>
        </div>

        {deniedItems.length === 0 ? (
          <p className="text-gray-500 text-sm">No denied claims. Submit and deny claims from the Pipeline view first.</p>
        ) : (
          <div className="space-y-3">
            {deniedItems.map(item => (
              <div
                key={item.id}
                className={`border rounded-lg p-4 cursor-pointer hover:shadow-md transition ${
                  selectedItem?.id === item.id ? 'border-blue-400 bg-blue-50' : 'border-gray-200'
                }`}
                onClick={() => { setSelectedItem(item); setAppealText(item.appeal_text || ''); }}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-sm text-gray-600">{item.id}</span>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      item.status === 'denied' ? 'bg-red-100 text-red-800' : 'bg-orange-100 text-orange-800'
                    }`}>
                      {item.status}
                    </span>
                  </div>
                  <span className="text-sm font-bold text-gray-900">
                    ${item.total_charge.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                  </span>
                </div>
                <div className="text-sm text-gray-900 font-medium">{item.patient_name}</div>
                <div className="flex items-center gap-4 mt-1 text-xs text-gray-500">
                  <span>CPT: {item.cpt_codes.join(', ')}</span>
                  <span>Payer: {item.payer_name}</span>
                </div>
                {item.denial_code && (
                  <div className="mt-2 p-2 bg-red-50 rounded text-xs">
                    <span className="font-medium text-red-800">{item.denial_code}:</span>{' '}
                    <span className="text-red-600">{item.denial_reason}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {selectedItem && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Appeal for {selectedItem.id}
          </h3>

          <div className="grid grid-cols-2 gap-3 text-sm mb-4">
            <div><span className="text-gray-500">Patient:</span> <span className="font-medium">{selectedItem.patient_name}</span></div>
            <div><span className="text-gray-500">Denial Code:</span> <span className="font-medium text-red-700">{selectedItem.denial_code}</span></div>
            <div><span className="text-gray-500">Payer:</span> <span className="font-medium">{selectedItem.payer_name}</span></div>
            <div><span className="text-gray-500">Charge:</span> <span className="font-medium">${selectedItem.total_charge.toLocaleString()}</span></div>
          </div>

          {selectedItem.status === 'denied' && !appealText && (
            <button
              onClick={() => handleAppeal(selectedItem.id)}
              disabled={appealLoading}
              className="px-4 py-2 bg-orange-600 text-white text-sm font-medium rounded-lg hover:bg-orange-700 disabled:opacity-50"
            >
              {appealLoading ? 'Generating Appeal...' : 'Generate Appeal Letter'}
            </button>
          )}

          {appealText && (
            <div className="mt-4">
              <h4 className="text-sm font-semibold text-gray-700 mb-2">Appeal Letter</h4>
              <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                <pre className="text-sm text-gray-800 whitespace-pre-wrap font-sans">{appealText}</pre>
              </div>
              <button
                onClick={() => navigator.clipboard.writeText(appealText)}
                className="mt-2 px-3 py-1 text-xs text-blue-600 hover:text-blue-800 font-medium"
              >
                Copy to Clipboard
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
