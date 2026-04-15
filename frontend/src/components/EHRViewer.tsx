import React, { useState, useEffect } from 'react';
import { v2api, type PatientSummary, type EncounterSummary } from '../lib/v2api';

interface EHRViewerProps {
  onSelectEncounter?: (encounterId: string, patientId: string) => void;
}

export function EHRViewer({ onSelectEncounter }: EHRViewerProps) {
  const [patients, setPatients] = useState<PatientSummary[]>([]);
  const [selectedPatient, setSelectedPatient] = useState<string | null>(null);
  const [encounters, setEncounters] = useState<EncounterSummary[]>([]);
  const [expandedNote, setExpandedNote] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    v2api.getPatients()
      .then(data => { setPatients(data.patients); setLoading(false); })
      .catch(err => { setError(err.message); setLoading(false); });
  }, []);

  useEffect(() => {
    if (!selectedPatient) { setEncounters([]); return; }
    v2api.getPatientEncounters(selectedPatient)
      .then(data => setEncounters(data.encounters))
      .catch(err => setError(err.message));
  }, [selectedPatient]);

  if (loading) return <div className="p-8 text-center text-gray-500">Loading patients...</div>;
  if (error) return <div className="p-8 text-center text-red-500">Error: {error}</div>;

  const selected = patients.find(p => p.id === selectedPatient);

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">EHR Patient Registry</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-left text-gray-500">
                <th className="pb-2 pr-4">Patient</th>
                <th className="pb-2 pr-4">DOB</th>
                <th className="pb-2 pr-4">Gender</th>
                <th className="pb-2 pr-4">Payer</th>
                <th className="pb-2 pr-4">Conditions</th>
                <th className="pb-2 pr-4">Encounters</th>
                <th className="pb-2"></th>
              </tr>
            </thead>
            <tbody>
              {patients.map(p => (
                <tr
                  key={p.id}
                  className={`border-b border-gray-50 cursor-pointer hover:bg-blue-50 transition ${selectedPatient === p.id ? 'bg-blue-50' : ''}`}
                  onClick={() => setSelectedPatient(p.id)}
                >
                  <td className="py-2 pr-4 font-medium text-gray-900">{p.name}</td>
                  <td className="py-2 pr-4 text-gray-600">{p.birthDate}</td>
                  <td className="py-2 pr-4 text-gray-600 capitalize">{p.gender}</td>
                  <td className="py-2 pr-4">
                    <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-700">{p.payer}</span>
                  </td>
                  <td className="py-2 pr-4 text-gray-500 text-xs">{p.conditions.slice(0, 3).join(', ')}{p.conditions.length > 3 ? '...' : ''}</td>
                  <td className="py-2 pr-4 text-gray-600">{p.encounter_count}</td>
                  <td className="py-2">
                    <button
                      className="text-blue-600 hover:text-blue-800 text-xs font-medium"
                      onClick={(e) => { e.stopPropagation(); setSelectedPatient(p.id); }}
                    >
                      View
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {selected && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">{selected.name}</h3>
            <span className="text-sm text-gray-500">{selected.id}</span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6 text-sm">
            <div><span className="text-gray-500">DOB:</span> <span className="font-medium">{selected.birthDate}</span></div>
            <div><span className="text-gray-500">Gender:</span> <span className="font-medium capitalize">{selected.gender}</span></div>
            <div><span className="text-gray-500">Payer:</span> <span className="font-medium">{selected.payer}</span></div>
            <div><span className="text-gray-500">Plan:</span> <span className="font-medium">{selected.plan}</span></div>
            <div><span className="text-gray-500">Member ID:</span> <span className="font-medium">{selected.member_id}</span></div>
            <div className="col-span-2 md:col-span-3">
              <span className="text-gray-500">Conditions:</span>{' '}
              <span className="font-medium">{selected.conditions.join(', ')}</span>
            </div>
          </div>

          <h4 className="text-sm font-semibold text-gray-700 mb-3">Encounters ({encounters.length})</h4>
          <div className="space-y-3">
            {encounters.map(enc => (
              <div key={enc.id} className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-medium text-gray-900">{enc.date}</span>
                    <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">{enc.type}</span>
                    <span className="text-sm text-gray-500">{enc.provider}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      className="text-xs text-gray-500 hover:text-gray-700"
                      onClick={() => setExpandedNote(expandedNote === enc.id ? null : enc.id)}
                    >
                      {expandedNote === enc.id ? 'Hide Note' : 'Show Note'}
                    </button>
                    {onSelectEncounter && (
                      <button
                        className="px-3 py-1 text-xs font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700"
                        onClick={() => onSelectEncounter(enc.id, selected.id)}
                      >
                        Process Claim
                      </button>
                    )}
                  </div>
                </div>
                <div className="text-xs text-gray-500">{enc.facility}</div>
                {expandedNote === enc.id && (
                  <div className="mt-3 p-3 bg-gray-50 rounded text-sm text-gray-700 whitespace-pre-wrap">
                    {enc.clinical_note}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
