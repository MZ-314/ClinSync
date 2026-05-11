import { Link, useParams } from 'react-router';
import {
  Activity,
  Pill,
  AlertTriangle,
  Heart,
  Loader,
  Stethoscope,
  ArrowRight,
  FlaskConical,
} from 'lucide-react';

import EntityCard from '../components/entities/EntityCard';
import WorkflowTimeline from '../components/common/WorkflowTimeline';
import Badge from '../components/common/Badge';
import { statusLabel, statusToWorkflowStep, useConsultation } from '../lib/hooks';

export default function ClinicalEntities() {
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

  const extracted = data.extracted_entities;

  const toEntities = (items: string[]) =>
    items.map((value) => ({ value, confidence: 0.9 }));

  const medicationEntities =
    extracted?.medications.map((m) => ({
      value: [m.name, m.dosage, m.frequency].filter(Boolean).join(' — '),
      confidence: 0.9,
    })) ?? [];

  const vitalEntities =
    extracted?.vitals.map((v) => ({
      value: `${v.name}: ${v.value}${v.unit ? ' ' + v.unit : ''}`,
      confidence: 0.95,
    })) ?? [];

  const symptomEntities = toEntities(extracted?.symptoms ?? []);
  const diagnosisEntities = toEntities(extracted?.diagnosis ?? []);
  const labTestEntities = toEntities(extracted?.lab_tests ?? []);

  const totalEntities =
    symptomEntities.length +
    vitalEntities.length +
    diagnosisEntities.length +
    medicationEntities.length +
    labTestEntities.length;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">
            Clinical Entity Extraction
          </h1>
          <p className="text-sm text-gray-600 mt-1 font-mono">
            {data.consultation_id}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="info">{statusLabel(data.status)}</Badge>
          <Link
            to={`/medical-coding/${data.consultation_id}`}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2 text-sm font-medium"
          >
            Next: Codes <ArrowRight size={16} />
          </Link>
        </div>
      </div>

      <WorkflowTimeline currentStep={statusToWorkflowStep(data.status)} />

      {!extracted ? (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 text-blue-800 text-sm flex items-center gap-3">
          <Loader className="animate-spin" size={18} />
          Waiting for extraction to complete…
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <EntityCard
              title="Symptoms"
              entities={symptomEntities}
              icon={Activity}
              color="blue"
            />
            <EntityCard
              title="Vital Signs"
              entities={vitalEntities}
              icon={Heart}
              color="red"
            />
            <EntityCard
              title="Diagnoses"
              entities={diagnosisEntities}
              icon={Stethoscope}
              color="purple"
            />
            <EntityCard
              title="Medications"
              entities={medicationEntities}
              icon={Pill}
              color="green"
            />
            <EntityCard
              title="Lab Tests Ordered"
              entities={labTestEntities}
              icon={FlaskConical}
              color="orange"
            />
          </div>

          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <p className="text-sm text-gray-600 mb-2">Entities Extracted</p>
                <p className="text-2xl font-semibold text-gray-900">
                  {totalEntities}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-600 mb-2">Chief Complaint</p>
                <p className="text-sm text-gray-900">
                  {extracted.chief_complaint ?? '—'}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-600 mb-2">Follow-up</p>
                <p className="text-sm text-gray-900">
                  {extracted.follow_up ?? '—'}
                </p>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
