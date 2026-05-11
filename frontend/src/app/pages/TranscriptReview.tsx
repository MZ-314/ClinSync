import { Link, useParams } from 'react-router';
import { Loader, AlertTriangle, ArrowRight } from 'lucide-react';

import WorkflowTimeline from '../components/common/WorkflowTimeline';
import Badge from '../components/common/Badge';
import { statusLabel, statusToWorkflowStep, useConsultation } from '../lib/hooks';

export default function TranscriptReview() {
  const { id } = useParams<{ id: string }>();
  const { data, loading, error } = useConsultation(id);

  if (!id) {
    return (
      <EmptyState
        title="No Consultation Selected"
        body="Open a consultation from the Dashboard or start a new one."
      />
    );
  }

  if (loading && !data) {
    return <LoadingState />;
  }

  if (error) {
    return <ErrorState message={error} />;
  }

  if (!data) {
    return <EmptyState title="Not Found" body="That consultation does not exist." />;
  }

  const extracted = data.extracted_entities;
  const chiefComplaint = extracted?.chief_complaint;
  const symptoms = extracted?.symptoms ?? [];
  const vitals = extracted?.vitals ?? [];
  const diagnoses = extracted?.diagnosis ?? [];
  const medications = extracted?.medications ?? [];
  const labTests = extracted?.lab_tests ?? [];
  const followUp = extracted?.follow_up;
  const notes = extracted?.notes;

  const transcriptText = data.transcript ?? '';
  const transcriptSegments = transcriptText
    .split(/(?<=[.!?])\s+/)
    .map((s) => s.trim())
    .filter((s) => s.length > 0);

  const isProcessing = [
    'uploaded',
    'transcribing',
    'transcribed',
    'extracting',
  ].includes(data.status);

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Transcript Review</h1>
          <p className="text-sm text-gray-600 mt-1 font-mono">{data.consultation_id}</p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="info">{statusLabel(data.status)}</Badge>
          <Link
            to={`/clinical-entities/${data.consultation_id}`}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2 text-sm font-medium"
          >
            Next: Entities <ArrowRight size={16} />
          </Link>
        </div>
      </div>

      <WorkflowTimeline currentStep={statusToWorkflowStep(data.status)} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg border border-gray-200">
          <div className="p-4 border-b border-gray-200 flex items-center justify-between">
            <h3 className="font-medium text-gray-900">Transcript</h3>
            <span className="text-sm text-gray-600">
              {transcriptSegments.length} segments
              {data.language ? ` · ${data.language}` : ''}
            </span>
          </div>
          <div className="p-4 space-y-4 max-h-[700px] overflow-y-auto">
            {transcriptSegments.length === 0 ? (
              <p className="text-sm text-gray-500 text-center py-10">
                Transcript not yet available.
              </p>
            ) : (
              transcriptSegments.map((seg, i) => (
                <div key={i} className="p-4 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-700 leading-relaxed">{seg}</p>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="bg-white rounded-lg border border-gray-200">
          <div className="p-4 border-b border-gray-200">
            <h3 className="font-medium text-gray-900">Clinical Summary</h3>
          </div>
          <div className="p-6 space-y-6 max-h-[700px] overflow-y-auto">
            {isProcessing && !extracted && (
              <div className="flex items-center gap-2 text-blue-700 bg-blue-50 p-3 rounded-lg text-sm">
                <Loader className="animate-spin" size={16} />
                Extraction in progress…
              </div>
            )}

            {chiefComplaint && (
              <Section title="Chief Complaint">
                <div className="p-4 bg-blue-50 rounded-lg border border-blue-100">
                  <p className="text-sm text-gray-700">{chiefComplaint}</p>
                </div>
              </Section>
            )}

            {symptoms.length > 0 && (
              <Section title="Symptoms">
                <ListItems items={symptoms} />
              </Section>
            )}

            {vitals.length > 0 && (
              <Section title="Vital Signs">
                <div className="grid grid-cols-2 gap-3">
                  {vitals.map((v, i) => (
                    <div
                      key={i}
                      className="p-3 bg-purple-50 rounded-lg border border-purple-100"
                    >
                      <p className="text-xs text-purple-600 mb-1">{v.name}</p>
                      <p className="text-sm font-medium text-gray-900">
                        {v.value}
                        {v.unit ? ` ${v.unit}` : ''}
                      </p>
                    </div>
                  ))}
                </div>
              </Section>
            )}

            {diagnoses.length > 0 && (
              <Section title="Diagnoses">
                <ListItems items={diagnoses} variant="green" />
              </Section>
            )}

            {medications.length > 0 && (
              <Section title="Medications">
                <div className="space-y-2">
                  {medications.map((m, i) => (
                    <div
                      key={i}
                      className="p-3 bg-green-50 rounded-lg border border-green-100"
                    >
                      <p className="text-sm font-medium text-gray-900">{m.name}</p>
                      <p className="text-xs text-gray-600 mt-1">
                        {[m.dosage, m.frequency, m.duration && `for ${m.duration}`]
                          .filter(Boolean)
                          .join(' · ')}
                      </p>
                    </div>
                  ))}
                </div>
              </Section>
            )}

            {labTests.length > 0 && (
              <Section title="Lab Tests Ordered">
                <ListItems items={labTests} variant="orange" />
              </Section>
            )}

            {followUp && (
              <Section title="Follow-up">
                <div className="p-3 bg-orange-50 rounded-lg border border-orange-100">
                  <p className="text-sm text-gray-700">{followUp}</p>
                </div>
              </Section>
            )}

            {notes && (
              <Section title="Notes">
                <p className="text-sm text-gray-700">{notes}</p>
              </Section>
            )}

            {!extracted && !isProcessing && (
              <p className="text-sm text-gray-500">
                No clinical entities extracted yet.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h4 className="text-sm font-medium text-gray-900 mb-2">{title}</h4>
      {children}
    </div>
  );
}

function ListItems({
  items,
  variant = 'gray',
}: {
  items: string[];
  variant?: 'gray' | 'green' | 'orange';
}) {
  const cls =
    variant === 'green'
      ? 'bg-green-50 border-green-100'
      : variant === 'orange'
      ? 'bg-orange-50 border-orange-100'
      : 'bg-gray-50 border-gray-100';
  return (
    <div className="space-y-2">
      {items.map((s, i) => (
        <div key={i} className={`p-3 rounded-lg border ${cls}`}>
          <p className="text-sm text-gray-700">• {s}</p>
        </div>
      ))}
    </div>
  );
}

function LoadingState() {
  return (
    <div className="p-10 flex items-center justify-center text-gray-500">
      <Loader className="animate-spin mr-2" size={20} /> Loading consultation…
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="p-6">
      <div className="flex items-start gap-3 text-red-700 bg-red-50 border border-red-200 rounded-lg p-4">
        <AlertTriangle size={20} className="mt-0.5" />
        <div>
          <p className="font-medium">Failed to load consultation</p>
          <p className="text-sm">{message}</p>
        </div>
      </div>
    </div>
  );
}

function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <div className="p-10 text-center text-gray-500">
      <h2 className="text-lg font-semibold text-gray-900 mb-2">{title}</h2>
      <p className="text-sm mb-4">{body}</p>
      <Link to="/" className="text-blue-600 hover:underline text-sm">
        Back to Dashboard
      </Link>
    </div>
  );
}
