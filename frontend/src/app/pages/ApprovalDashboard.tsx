import { useState } from 'react';
import { Link, useParams } from 'react-router';
import { toast } from 'sonner';
import { AlertCircle, AlertTriangle, Loader } from 'lucide-react';

import ApprovalPanel from '../components/review/ApprovalPanel';
import WorkflowTimeline from '../components/common/WorkflowTimeline';
import { ApiError, submitApproval } from '../lib/api';
import { statusLabel, statusToWorkflowStep, useConsultation } from '../lib/hooks';

export default function ApprovalDashboard() {
  const { id } = useParams<{ id: string }>();
  const { data, loading, error, refetch } = useConsultation(id);
  const [activeTab, setActiveTab] = useState<'entities' | 'fhir'>('entities');
  const [submitting, setSubmitting] = useState<'approved' | 'rejected' | null>(null);

  if (!id) {
    return (
      <div className="p-10 text-center text-gray-500">
        <h2 className="text-lg font-semibold text-gray-900 mb-2">
          No Consultation Selected
        </h2>
        <Link to="/" className="text-blue-600 hover:underline text-sm">
          Back to Dashboard
        </Link>
      </div>
    );
  }

  if (loading && !data) {
    return (
      <div className="p-10 flex items-center justify-center text-gray-500">
        <Loader className="animate-spin mr-2" size={20} /> Loading…
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6">
        <div className="flex items-start gap-3 text-red-700 bg-red-50 border border-red-200 rounded-lg p-4">
          <AlertTriangle size={20} className="mt-0.5" />
          <p className="text-sm">{error ?? 'Consultation not found.'}</p>
        </div>
      </div>
    );
  }

  const extracted = data.extracted_entities;
  const coding = data.coded_data;
  const transcriptSegments = (data.transcript ?? '')
    .split(/(?<=[.!?])\s+/)
    .map((s) => s.trim())
    .filter(Boolean);

  const handleDecision = async (decision: 'approved' | 'rejected', notes: string) => {
    setSubmitting(decision);
    try {
      await submitApproval(data.consultation_id, {
        decision,
        reviewer_id: 'doctor',
        reviewer_name: data.doctor_name ?? undefined,
        notes,
      });
      toast.success(
        decision === 'approved'
          ? 'Consultation approved.'
          : 'Consultation rejected.',
      );
      await refetch();
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
          ? err.message
          : 'Approval failed.';
      toast.error(message);
    } finally {
      setSubmitting(null);
    }
  };

  const isPendingReview = data.status === 'pending_review';

  const diagnosisRows =
    coding?.diagnoses.map((d) => ({
      condition: d.term,
      code: [
        d.icd11_code && `ICD-11: ${d.icd11_code}`,
        d.snomed_code && `SNOMED: ${d.snomed_code}`,
      ]
        .filter(Boolean)
        .join(' | ') || '—',
    })) ?? [];

  const medicationRows =
    extracted?.medications.map((m) => ({
      name: m.name,
      dosage: m.dosage || '—',
      frequency: m.frequency || '—',
    })) ?? [];

  const approvalData = {
    patientId: extracted?.patient_age
      ? `Age ${extracted.patient_age}${extracted.patient_gender ? ' · ' + extracted.patient_gender : ''}`
      : data.consultation_id.slice(0, 8),
    consultationDate: data.created_at
      ? new Date(data.created_at).toLocaleString()
      : '',
    provider: data.doctor_name || 'Unknown',
    status: statusLabel(data.status),
    chiefComplaint: extracted?.chief_complaint || 'Not extracted',
    diagnoses: diagnosisRows.length
      ? diagnosisRows
      : [{ condition: 'No diagnosis extracted', code: '' }],
    medications: medicationRows,
    confidenceScore: 87,
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">
          Human-in-the-Loop Approval
        </h1>
        <p className="text-sm text-gray-600 mt-1 font-mono">
          {data.consultation_id}
        </p>
      </div>

      <WorkflowTimeline currentStep={statusToWorkflowStep(data.status)} />

      {!isPendingReview && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-start gap-3">
          <AlertCircle size={20} className="text-blue-600 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-blue-900">
              Current status: {statusLabel(data.status)}
            </p>
            <p className="text-sm text-blue-700 mt-1">
              {data.status === 'approved' || data.status === 'submitted'
                ? 'This consultation has been approved.'
                : data.status === 'rejected'
                ? 'This consultation was rejected.'
                : 'The pipeline is still running. The approval form will activate once the consultation reaches Pending Review.'}
            </p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-12 gap-6 min-h-[800px]">
        <div className="col-span-12 lg:col-span-3 bg-white rounded-lg border border-gray-200 overflow-hidden flex flex-col">
          <div className="p-4 border-b border-gray-200">
            <h3 className="font-medium text-gray-900">Transcript</h3>
          </div>
          <div className="p-4 space-y-3 overflow-y-auto flex-1 max-h-[800px]">
            {transcriptSegments.length === 0 ? (
              <p className="text-sm text-gray-500">Transcript not available.</p>
            ) : (
              transcriptSegments.map((seg, index) => (
                <div key={index} className="p-3 bg-gray-50 rounded-lg">
                  <p className="text-xs text-gray-700 leading-relaxed">{seg}</p>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="col-span-12 lg:col-span-5 bg-white rounded-lg border border-gray-200 overflow-hidden flex flex-col">
          <div className="border-b border-gray-200">
            <div className="flex">
              <button
                onClick={() => setActiveTab('entities')}
                className={`flex-1 px-4 py-3 text-sm font-medium ${
                  activeTab === 'entities'
                    ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50'
                    : 'text-gray-600 hover:bg-gray-50'
                }`}
              >
                Extracted Entities
              </button>
              <button
                onClick={() => setActiveTab('fhir')}
                className={`flex-1 px-4 py-3 text-sm font-medium ${
                  activeTab === 'fhir'
                    ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50'
                    : 'text-gray-600 hover:bg-gray-50'
                }`}
              >
                Coded Data
              </button>
            </div>
          </div>

          <div className="p-6 overflow-y-auto flex-1 max-h-[800px]">
            {activeTab === 'entities' && (
              <div className="space-y-6 text-sm">
                {extracted ? (
                  <>
                    {extracted.symptoms.length > 0 && (
                      <Section title="Symptoms">
                        {extracted.symptoms.map((s, i) => (
                          <Item key={i}>{s}</Item>
                        ))}
                      </Section>
                    )}
                    {extracted.vitals.length > 0 && (
                      <Section title="Vital Signs">
                        <div className="grid grid-cols-2 gap-3">
                          {extracted.vitals.map((v, i) => (
                            <div
                              key={i}
                              className="p-3 bg-purple-50 rounded-lg border border-purple-100"
                            >
                              <p className="text-xs text-purple-600 mb-1">{v.name}</p>
                              <p className="text-sm font-medium">
                                {v.value}
                                {v.unit ? ` ${v.unit}` : ''}
                              </p>
                            </div>
                          ))}
                        </div>
                      </Section>
                    )}
                    {extracted.diagnosis.length > 0 && (
                      <Section title="Diagnoses">
                        {extracted.diagnosis.map((d, i) => (
                          <Item key={i} variant="green">
                            {d}
                          </Item>
                        ))}
                      </Section>
                    )}
                    {extracted.medications.length > 0 && (
                      <Section title="Medications">
                        {extracted.medications.map((m, i) => (
                          <Item key={i}>
                            {[m.name, m.dosage, m.frequency]
                              .filter(Boolean)
                              .join(' — ')}
                          </Item>
                        ))}
                      </Section>
                    )}
                    {extracted.lab_tests.length > 0 && (
                      <Section title="Lab Tests">
                        {extracted.lab_tests.map((l, i) => (
                          <Item key={i} variant="orange">
                            {l}
                          </Item>
                        ))}
                      </Section>
                    )}
                  </>
                ) : (
                  <p className="text-gray-500">No entities extracted yet.</p>
                )}
              </div>
            )}

            {activeTab === 'fhir' && (
              <div className="space-y-4 text-xs">
                {coding ? (
                  <pre className="p-4 bg-gray-50 rounded-lg border border-gray-200 overflow-x-auto">
                    {JSON.stringify(coding, null, 2)}
                  </pre>
                ) : (
                  <p className="text-gray-500">No coded data yet.</p>
                )}
              </div>
            )}
          </div>
        </div>

        <div className="col-span-12 lg:col-span-4">
          <ApprovalPanel
            data={approvalData}
            onApprove={() => handleDecision('approved', '')}
            onReject={() => handleDecision('rejected', '')}
            onSendBack={() => toast.info('Send-back not yet supported by backend.')}
          />
          {!isPendingReview && (
            <p className="text-xs text-gray-500 mt-3 text-center">
              Approval is disabled until the consultation reaches Pending Review.
            </p>
          )}
          {submitting && (
            <p className="text-xs text-blue-600 mt-3 text-center">
              Submitting {submitting}…
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h4 className="text-sm font-medium text-gray-900 mb-3">{title}</h4>
      <div className="space-y-2">{children}</div>
    </div>
  );
}

function Item({
  children,
  variant,
}: {
  children: React.ReactNode;
  variant?: 'green' | 'orange';
}) {
  const cls =
    variant === 'green'
      ? 'bg-green-50 border-green-100'
      : variant === 'orange'
      ? 'bg-orange-50 border-orange-100'
      : 'bg-blue-50 border-blue-100';
  return (
    <div className={`p-3 rounded-lg border ${cls}`}>
      <p className="text-sm text-gray-700">{children}</p>
    </div>
  );
}
