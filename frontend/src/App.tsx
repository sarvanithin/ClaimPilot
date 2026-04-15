import React, { useState } from 'react';
import { ClaimInput } from './components/ClaimInput';
import { DenialAnalysis } from './components/DenialAnalysis';
import { PolicyMatches } from './components/PolicyMatches';
import { AppealPreview } from './components/AppealPreview';
import { StatusTracker } from './components/StatusTracker';
import { EHRViewer } from './components/EHRViewer';
import { ChargeCapture } from './components/ChargeCapture';
import { ClaimScrubber } from './components/ClaimScrubber';
import { ClaimsPipeline } from './components/ClaimsPipeline';
import { DenialManager } from './components/DenialManager';
import type { AgentStep } from './components/StatusTracker';
import { analyzeClaim } from './lib/api';
import { v2api } from './lib/v2api';
import type { Claim, AppealResult } from './lib/api';
import { Activity } from 'lucide-react';

type TabId = 'appeal' | 'ehr' | 'charges' | 'scrubber' | 'pipeline' | 'denials';

const TABS: { id: TabId; label: string }[] = [
  { id: 'appeal', label: 'Appeal Agent' },
  { id: 'ehr', label: 'EHR Viewer' },
  { id: 'charges', label: 'Charge Capture' },
  { id: 'scrubber', label: 'Claim Scrubber' },
  { id: 'pipeline', label: 'Pipeline' },
  { id: 'denials', label: 'Denial Manager' },
];

function App() {
  const [activeTab, setActiveTab] = useState<TabId>('appeal');
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<AppealResult | null>(null);
  const [steps, setSteps] = useState<AgentStep[]>([
    { id: '1', label: 'Classify Denial', status: 'pending' },
    { id: '2', label: 'Retrieve Policy Context', status: 'pending' },
    { id: '3', label: 'Analyze Medical Necessity', status: 'pending' },
    { id: '4', label: 'Draft Appeal Letter', status: 'pending' },
    { id: '5', label: 'Self-Critique & Refine', status: 'pending' },
  ]);

  // State for cross-tab interaction
  const [selectedEncounterId, setSelectedEncounterId] = useState<string>('');
  const [submitMessage, setSubmitMessage] = useState('');

  const handleSubmitClaim = async (claim: Claim) => {
    setIsLoading(true);
    setResult(null);
    setSteps(steps.map(s => ({ ...s, status: 'pending' })));

    setTimeout(() => setSteps(s => s.map((step, i) => i === 0 ? { ...step, status: 'active' } : step)), 500);
    setTimeout(() => setSteps(s => s.map((step, i) => i === 0 ? { ...step, status: 'complete' } : i === 1 ? { ...step, status: 'active' } : step)), 1500);
    setTimeout(() => setSteps(s => s.map((step, i) => i === 1 ? { ...step, status: 'complete' } : i === 2 ? { ...step, status: 'active' } : step)), 3000);
    setTimeout(() => setSteps(s => s.map((step, i) => i === 2 ? { ...step, status: 'complete' } : i === 3 ? { ...step, status: 'active' } : step)), 4500);
    setTimeout(() => setSteps(s => s.map((step, i) => i === 3 ? { ...step, status: 'complete' } : i === 4 ? { ...step, status: 'active' } : step)), 6500);

    try {
      const response = await analyzeClaim(claim);
      setResult(response);
      setSteps(s => s.map(step => ({ ...step, status: 'complete' })));
    } catch (error) {
      console.error('Failed to analyze claim:', error);
      alert('Failed to analyze claim. Ensure the backend is running.');
      setSteps(s => s.map(step => step.status === 'active' ? { ...step, status: 'error' } : step));
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectEncounter = async (encounterId: string, patientId: string) => {
    setSubmitMessage('');
    try {
      const result = await v2api.submitClaim(encounterId, patientId);
      setSubmitMessage(`Claim ${result.claim_id} submitted successfully (${result.scrub_result.status}).`);
      setSelectedEncounterId(encounterId);
    } catch (err: any) {
      setSubmitMessage(`Error: ${err.message}`);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="h-16 flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center shadow-lg shadow-blue-500/20">
              <Activity className="text-white w-5 h-5" />
            </div>
            <h1 className="text-xl font-bold bg-gradient-to-r from-gray-900 to-gray-600 bg-clip-text text-transparent">
              ClaimPilot
            </h1>
            <span className="ml-2 px-2.5 py-0.5 rounded-full bg-blue-50 text-blue-700 text-xs font-medium border border-blue-100">
              v2 RCM Agent
            </span>
          </div>
          <nav className="flex gap-1 -mb-px">
            {TABS.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
                  activeTab === tab.id
                    ? 'border-blue-600 text-blue-700'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full">
        {/* V1: Appeal Agent */}
        {activeTab === 'appeal' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
            <div className="lg:col-span-5 space-y-6">
              <ClaimInput onSubmit={handleSubmitClaim} isLoading={isLoading} />
            </div>
            <div className="lg:col-span-7 space-y-6">
              {isLoading && <StatusTracker steps={steps} />}
              {!isLoading && !result && (
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-12 flex flex-col items-center justify-center text-center">
                  <h3 className="text-lg font-medium text-gray-900">Waiting for Data</h3>
                  <p className="text-gray-500 mt-2 max-w-md">
                    Enter claim details and clinical notes on the left. ClaimPilot will classify the denial, retrieve relevant policy, and draft an appeal.
                  </p>
                </div>
              )}
              {result && (
                <div className="space-y-6">
                  <DenialAnalysis analysis={result.analysis} />
                  <PolicyMatches policies={result.policies} />
                  <AppealPreview appeal={result.appeal} />
                </div>
              )}
            </div>
          </div>
        )}

        {/* V2: EHR Viewer */}
        {activeTab === 'ehr' && (
          <div>
            {submitMessage && (
              <div className={`mb-4 p-3 rounded-lg text-sm ${submitMessage.startsWith('Error') ? 'bg-red-50 text-red-700' : 'bg-green-50 text-green-700'}`}>
                {submitMessage}
              </div>
            )}
            <EHRViewer onSelectEncounter={handleSelectEncounter} />
          </div>
        )}

        {/* V2: Charge Capture */}
        {activeTab === 'charges' && (
          <ChargeCapture encounterId={selectedEncounterId} />
        )}

        {/* V2: Claim Scrubber */}
        {activeTab === 'scrubber' && (
          <ClaimScrubber />
        )}

        {/* V2: Pipeline */}
        {activeTab === 'pipeline' && (
          <ClaimsPipeline />
        )}

        {/* V2: Denial Manager */}
        {activeTab === 'denials' && (
          <DenialManager />
        )}
      </main>
    </div>
  );
}

export default App;
