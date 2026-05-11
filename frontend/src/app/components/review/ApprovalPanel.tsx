import { useState } from 'react';
import { CheckCircle, XCircle, ArrowLeft, Edit2 } from 'lucide-react';
import Badge from '../common/Badge';

interface ApprovalData {
  patientId: string;
  consultationDate: string;
  provider: string;
  status: string;
  chiefComplaint: string;
  diagnoses: Array<{
    condition: string;
    code: string;
  }>;
  medications: Array<{
    name: string;
    dosage: string;
    frequency: string;
  }>;
  confidenceScore: number;
}

interface ApprovalPanelProps {
  data: ApprovalData;
  onApprove: () => void;
  onReject: () => void;
  onSendBack: () => void;
}

export default function ApprovalPanel({ data, onApprove, onReject, onSendBack }: ApprovalPanelProps) {
  const [reviewNotes, setReviewNotes] = useState('');
  const [editMode, setEditMode] = useState<Record<string, boolean>>({});

  const handleToggleEdit = (field: string) => {
    setEditMode(prev => ({ ...prev, [field]: !prev[field] }));
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 h-full flex flex-col">
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Review & Approve</h2>
          <Badge variant="warning">Pending Review</Badge>
        </div>

        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-gray-500">Patient ID</p>
            <p className="font-medium">{data.patientId}</p>
          </div>
          <div>
            <p className="text-gray-500">Consultation Date</p>
            <p className="font-medium">{data.consultationDate}</p>
          </div>
          <div>
            <p className="text-gray-500">Provider</p>
            <p className="font-medium">{data.provider}</p>
          </div>
          <div>
            <p className="text-gray-500">Status</p>
            <p className="font-medium">{data.status}</p>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        <div>
          <h3 className="text-sm font-medium text-gray-900 mb-3">Chief Complaint</h3>
          <div className="bg-blue-50 p-4 rounded-lg border border-blue-100">
            <p className="text-sm text-gray-700">{data.chiefComplaint}</p>
          </div>
        </div>

        <div>
          <h3 className="text-sm font-medium text-gray-900 mb-3">Diagnosis</h3>
          <div className="space-y-2">
            {data.diagnoses.map((diagnosis, index) => (
              <div key={index} className="bg-gray-50 p-4 rounded-lg flex items-start justify-between group">
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-900">{diagnosis.condition}</p>
                  <p className="text-xs text-gray-500 mt-1">{diagnosis.code}</p>
                </div>
                <button
                  onClick={() => handleToggleEdit(`diagnosis-${index}`)}
                  className="opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  <Edit2 size={16} className="text-gray-600" />
                </button>
              </div>
            ))}
          </div>
        </div>

        <div>
          <h3 className="text-sm font-medium text-gray-900 mb-3">Medications Prescribed</h3>
          <div className="space-y-2">
            {data.medications.map((med, index) => (
              <div key={index} className="bg-gray-50 p-4 rounded-lg">
                <p className="text-sm font-medium text-gray-900">{med.name}</p>
                <p className="text-xs text-gray-500 mt-1">{med.dosage} - {med.frequency}</p>
              </div>
            ))}
          </div>
        </div>

        <div>
          <h3 className="text-sm font-medium text-gray-900 mb-3">Review Notes</h3>
          <textarea
            value={reviewNotes}
            onChange={(e) => setReviewNotes(e.target.value)}
            placeholder="Add notes about your review..."
            className="w-full p-4 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            rows={4}
          />
        </div>

        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <p className="text-sm font-medium text-yellow-900 mb-1">Confidence Score</p>
          <div className="flex items-center gap-3">
            <div className="flex-1 bg-yellow-100 rounded-full h-3">
              <div
                className="bg-yellow-500 h-3 rounded-full"
                style={{ width: `${data.confidenceScore}%` }}
              ></div>
            </div>
            <span className="text-sm font-medium text-yellow-900">{data.confidenceScore}%</span>
          </div>
          <p className="text-xs text-yellow-700 mt-2">AI extracted with high confidence. Manual review recommended.</p>
        </div>
      </div>

      <div className="p-6 border-t border-gray-200 space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <button
            onClick={onApprove}
            className="py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors flex items-center justify-center gap-2 font-medium"
          >
            <CheckCircle size={20} />
            Approve & Submit
          </button>
          <button
            onClick={onReject}
            className="py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors flex items-center justify-center gap-2 font-medium"
          >
            <XCircle size={20} />
            Reject
          </button>
        </div>
        <button
          onClick={onSendBack}
          className="w-full py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors flex items-center justify-center gap-2 font-medium"
        >
          <ArrowLeft size={20} />
          Send Back for Revision
        </button>
      </div>
    </div>
  );
}
