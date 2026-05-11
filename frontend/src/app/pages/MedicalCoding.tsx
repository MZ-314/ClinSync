import { Link, useParams } from 'react-router';
import { AlertTriangle, Loader, ArrowRight } from 'lucide-react';

import CodingTable from '../components/coding/CodingTable';
import WorkflowTimeline from '../components/common/WorkflowTimeline';
import Badge from '../components/common/Badge';
import { statusLabel, statusToWorkflowStep, useConsultation } from '../lib/hooks';

interface MedicalCodeRow {
  term: string;
  description: string;
  system: string;
  code: string;
  confidence: number;
  status: 'mapped' | 'pending' | 'failed';
}

export default function MedicalCoding() {
  const { id } = useParams<{ id: string }>();
  const { data, loading, error } = useConsultation(id);

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

  const coding = data.coded_data;

  const rows: MedicalCodeRow[] = [];

  if (coding) {
    for (const d of coding.diagnoses) {
      if (d.icd11_code) {
        rows.push({
          term: d.term,
          description: d.icd11_description || 'ICD-11 diagnosis code',
          system: 'ICD-11',
          code: d.icd11_code,
          confidence: 0.9,
          status: 'mapped',
        });
      }
      if (d.snomed_code) {
        rows.push({
          term: d.term,
          description: d.snomed_description || 'SNOMED CT diagnosis code',
          system: 'SNOMED CT',
          code: d.snomed_code,
          confidence: 0.88,
          status: 'mapped',
        });
      }
      if (!d.icd11_code && !d.snomed_code) {
        rows.push({
          term: d.term,
          description: 'Code not assigned',
          system: 'ICD-11',
          code: '—',
          confidence: 0.4,
          status: 'pending',
        });
      }
    }

    for (const s of coding.symptoms) {
      if (s.snomed_code) {
        rows.push({
          term: s.term,
          description: s.snomed_description || 'SNOMED CT symptom code',
          system: 'SNOMED CT',
          code: s.snomed_code,
          confidence: 0.85,
          status: 'mapped',
        });
      }
    }

    for (const m of coding.medications) {
      if (m.rxnorm_code) {
        rows.push({
          term: m.name,
          description: m.rxnorm_description || m.generic_name || 'RxNorm medication code',
          system: 'RxNorm',
          code: m.rxnorm_code,
          confidence: 0.9,
          status: 'mapped',
        });
      } else {
        rows.push({
          term: m.name,
          description: m.generic_name || 'Medication',
          system: 'RxNorm',
          code: '—',
          confidence: 0.5,
          status: 'pending',
        });
      }
    }
  }

  const mappedCount = rows.filter((r) => r.status === 'mapped').length;
  const pendingCount = rows.filter((r) => r.status === 'pending').length;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Medical Coding</h1>
          <p className="text-sm text-gray-600 mt-1 font-mono">
            {data.consultation_id}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="info">{statusLabel(data.status)}</Badge>
          <Link
            to={`/fhir-viewer/${data.consultation_id}`}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2 text-sm font-medium"
          >
            Next: FHIR <ArrowRight size={16} />
          </Link>
        </div>
      </div>

      <WorkflowTimeline currentStep={statusToWorkflowStep(data.status)} />

      {rows.length === 0 ? (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 text-blue-800 text-sm flex items-center gap-3">
          <Loader className="animate-spin" size={18} />
          Waiting for medical coding to complete…
        </div>
      ) : (
        <>
          <CodingTable codes={rows} />

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h3 className="text-sm font-medium text-gray-600 mb-2">
                Mapped
              </h3>
              <span className="text-3xl font-semibold text-green-600">
                {mappedCount}
              </span>
              <span className="text-sm text-gray-500 ml-2">/ {rows.length}</span>
            </div>
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h3 className="text-sm font-medium text-gray-600 mb-2">
                Pending
              </h3>
              <span className="text-3xl font-semibold text-orange-600">
                {pendingCount}
              </span>
              <span className="text-sm text-gray-500 ml-2">codes</span>
            </div>
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h3 className="text-sm font-medium text-gray-600 mb-2">
                Code Systems
              </h3>
              <p className="text-sm text-gray-900">ICD-11 · SNOMED CT · RxNorm</p>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
