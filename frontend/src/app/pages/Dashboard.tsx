import { Link } from 'react-router';
import {
  Activity,
  FileText,
  CheckCircle,
  Clock,
  TrendingUp,
  AlertTriangle,
  Loader,
  Plus,
} from 'lucide-react';

import StatusCard from '../components/common/StatusCard';
import WorkflowTimeline from '../components/common/WorkflowTimeline';
import Badge from '../components/common/Badge';
import {
  statusLabel,
  statusToWorkflowStep,
  useConsultations,
} from '../lib/hooks';
import type { ConsultationStatus } from '../lib/types';

function badgeVariant(
  status: ConsultationStatus,
): 'success' | 'info' | 'warning' | 'error' | 'default' {
  switch (status) {
    case 'approved':
    case 'submitted':
      return 'success';
    case 'pending_review':
      return 'warning';
    case 'failed':
    case 'rejected':
      return 'error';
    case 'uploaded':
    case 'transcribing':
    case 'transcribed':
    case 'extracting':
    case 'extracted':
    case 'coding':
    case 'coded':
    case 'building_fhir':
      return 'info';
    default:
      return 'default';
  }
}

export default function Dashboard() {
  const { data, loading, error, refetch } = useConsultations(10000);

  const consultations = data ?? [];

  const counts = {
    active: consultations.filter((c) =>
      [
        'uploaded',
        'transcribing',
        'transcribed',
        'extracting',
        'extracted',
        'coding',
        'coded',
        'building_fhir',
      ].includes(c.status),
    ).length,
    pending: consultations.filter((c) => c.status === 'pending_review').length,
    completed: consultations.filter(
      (c) => c.status === 'approved' || c.status === 'submitted',
    ).length,
    transcribed: consultations.filter(
      (c) => c.status !== 'uploaded' && c.status !== 'failed',
    ).length,
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Dashboard</h1>
          <p className="text-sm text-gray-600 mt-1">
            AI-powered clinical documentation overview
          </p>
        </div>
        <Link
          to="/live-consultation"
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2 font-medium text-sm"
        >
          <Plus size={18} />
          New Consultation
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatusCard
          icon={Activity}
          title="Active Consultations"
          value={String(counts.active)}
          subtitle="In pipeline"
          color="blue"
        />
        <StatusCard
          icon={FileText}
          title="Transcribed"
          value={String(counts.transcribed)}
          subtitle="Past & present"
          color="green"
        />
        <StatusCard
          icon={Clock}
          title="Pending Approvals"
          value={String(counts.pending)}
          subtitle="Needs review"
          color="orange"
        />
        <StatusCard
          icon={CheckCircle}
          title="Approved / Submitted"
          value={String(counts.completed)}
          subtitle="Total"
          color="purple"
        />
      </div>

      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Pipeline Stages
        </h2>
        <WorkflowTimeline currentStep={0} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg border border-gray-200">
          <div className="p-6 border-b border-gray-200 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">
              Recent Consultations
            </h2>
            <button
              onClick={() => refetch()}
              className="text-sm text-blue-600 hover:text-blue-700"
            >
              ↻ Refresh
            </button>
          </div>

          {loading && consultations.length === 0 ? (
            <div className="p-10 flex items-center justify-center text-gray-500">
              <Loader className="animate-spin mr-2" size={20} /> Loading…
            </div>
          ) : error ? (
            <div className="p-6 flex items-start gap-3 text-red-700 bg-red-50">
              <AlertTriangle size={20} className="mt-0.5" />
              <div>
                <p className="font-medium">Failed to load consultations</p>
                <p className="text-sm">{error}</p>
              </div>
            </div>
          ) : consultations.length === 0 ? (
            <div className="p-10 text-center text-gray-500">
              <p>No consultations yet.</p>
              <Link
                to="/live-consultation"
                className="text-blue-600 hover:underline text-sm"
              >
                Start a new consultation →
              </Link>
            </div>
          ) : (
            <div className="divide-y divide-gray-200 max-h-[480px] overflow-y-auto">
              {consultations.map((c) => {
                const step = statusToWorkflowStep(c.status);
                const createdAt = c.created_at
                  ? new Date(c.created_at).toLocaleString()
                  : '';
                return (
                  <Link
                    key={c.consultation_id}
                    to={`/transcript-review/${c.consultation_id}`}
                    className="block p-6 hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="min-w-0 pr-4">
                        <p className="font-medium text-gray-900 truncate">
                          {c.doctor_name || 'Unknown Doctor'}
                        </p>
                        <p className="text-xs text-gray-500 font-mono truncate">
                          {c.consultation_id}
                        </p>
                      </div>
                      <Badge variant={badgeVariant(c.status)} size="sm">
                        {statusLabel(c.status)}
                      </Badge>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-500">{createdAt}</span>
                      <span className="text-gray-500">Step {step}/7</span>
                    </div>
                    <div className="mt-3 bg-gray-200 rounded-full h-1.5">
                      <div
                        className={`h-1.5 rounded-full ${
                          c.status === 'failed' || c.status === 'rejected'
                            ? 'bg-red-500'
                            : step >= 7
                            ? 'bg-green-500'
                            : 'bg-blue-500'
                        }`}
                        style={{ width: `${(step / 7) * 100}%` }}
                      />
                    </div>
                  </Link>
                );
              })}
            </div>
          )}
        </div>

        <div className="bg-white rounded-lg border border-gray-200">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">
              Quick Tips
            </h2>
          </div>
          <div className="p-6 space-y-4 text-sm text-gray-600">
            <p>
              <strong className="text-gray-900">1.</strong> Click <em>New
              Consultation</em> to upload audio. The transcription runs
              synchronously and the rest of the pipeline continues in the
              background.
            </p>
            <p>
              <strong className="text-gray-900">2.</strong> Open any
              consultation here to review the transcript, extracted entities,
              ICD-11/SNOMED codes, and generated FHIR resources.
            </p>
            <p>
              <strong className="text-gray-900">3.</strong> Once a consultation
              reaches <Badge variant="warning" size="sm">Pending Review</Badge>,
              use the Approval Dashboard to approve or reject the documentation.
            </p>

            <div className="pt-4 border-t border-gray-200 flex items-center gap-2 text-green-600">
              <TrendingUp size={16} />
              <span className="text-sm font-medium">
                Backend & NeonDB connected
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
