import { Link, useParams } from 'react-router';
import { CheckCircle, AlertTriangle, Loader, Download, ArrowRight } from 'lucide-react';

import FHIRResourceCard from '../components/fhir/FHIRResourceCard';
import WorkflowTimeline from '../components/common/WorkflowTimeline';
import Badge from '../components/common/Badge';
import {
  statusLabel,
  statusToWorkflowStep,
  useConsultation,
  useFhirRecords,
} from '../lib/hooks';

export default function FHIRViewer() {
  const { id } = useParams<{ id: string }>();
  const consultation = useConsultation(id);
  const records = useFhirRecords(id);

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

  if ((consultation.loading && !consultation.data) || (records.loading && !records.data)) {
    return (
      <div className="p-10 flex items-center justify-center text-gray-500">
        <Loader className="animate-spin mr-2" size={20} /> Loading FHIR resources…
      </div>
    );
  }

  if (consultation.error || !consultation.data) {
    return (
      <div className="p-6">
        <div className="flex items-start gap-3 text-red-700 bg-red-50 border border-red-200 rounded-lg p-4">
          <AlertTriangle size={20} className="mt-0.5" />
          <p className="text-sm">
            {consultation.error ?? 'Consultation not found.'}
          </p>
        </div>
      </div>
    );
  }

  const fhirRecords = records.data ?? [];
  const allValid = fhirRecords.length > 0 && fhirRecords.every((r) => r.is_valid);
  const bundleJson = JSON.stringify(
    {
      resourceType: 'Bundle',
      type: 'collection',
      entry: fhirRecords.map((r) => ({ resource: r.resource_json })),
    },
    null,
    2,
  );

  const exportBundle = () => {
    const blob = new Blob([bundleJson], { type: 'application/fhir+json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `fhir-bundle-${id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">
            FHIR Resource Viewer
          </h1>
          <p className="text-sm text-gray-600 mt-1 font-mono">
            {consultation.data.consultation_id}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="info">{statusLabel(consultation.data.status)}</Badge>
          <button
            onClick={exportBundle}
            disabled={fhirRecords.length === 0}
            className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 flex items-center gap-2 text-sm font-medium disabled:opacity-50"
          >
            <Download size={18} />
            Export Bundle
          </button>
          <Link
            to={`/approval-dashboard/${consultation.data.consultation_id}`}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2 text-sm font-medium"
          >
            Approval <ArrowRight size={16} />
          </Link>
        </div>
      </div>

      <WorkflowTimeline currentStep={statusToWorkflowStep(consultation.data.status)} />

      {records.error && (
        <div className="flex items-start gap-3 text-red-700 bg-red-50 border border-red-200 rounded-lg p-4">
          <AlertTriangle size={20} className="mt-0.5" />
          <p className="text-sm">{records.error}</p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-sm font-medium text-gray-600 mb-2">
            Total Resources
          </h3>
          <span className="text-3xl font-semibold text-blue-600">
            {fhirRecords.length}
          </span>
          <p className="text-xs text-gray-500 mt-2">FHIR R4 compliant</p>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-sm font-medium text-gray-600 mb-2">
            Validation Status
          </h3>
          <div className="flex items-center gap-2">
            {fhirRecords.length === 0 ? (
              <Badge variant="default">Pending</Badge>
            ) : allValid ? (
              <>
                <CheckCircle size={20} className="text-green-600" />
                <Badge variant="success">All Valid</Badge>
              </>
            ) : (
              <>
                <AlertTriangle size={20} className="text-orange-600" />
                <Badge variant="warning">Needs Review</Badge>
              </>
            )}
          </div>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-sm font-medium text-gray-600 mb-2">
            Submitted to HAPI
          </h3>
          <span className="text-3xl font-semibold text-purple-600">
            {fhirRecords.filter((r) => r.is_submitted).length}
          </span>
          <span className="text-sm text-gray-500 ml-2">
            / {fhirRecords.length}
          </span>
        </div>
      </div>

      {fhirRecords.length === 0 ? (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 text-blue-800 text-sm flex items-center gap-3">
          <Loader className="animate-spin" size={18} />
          Waiting for FHIR generation to complete…
        </div>
      ) : (
        <div className="space-y-4">
          {fhirRecords.map((r) => (
            <FHIRResourceCard
              key={r.id}
              resource={{
                resourceType: r.resource_type,
                id: r.fhir_server_id || r.id,
                valid: r.is_valid,
                data: r.resource_json,
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
}
