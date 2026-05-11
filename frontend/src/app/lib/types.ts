// Types mirroring the backend Pydantic schemas.
// Keep these in sync with backend/app/api/consultations.py and approvals.py
// and the agent schemas under backend/app/agents/{extraction,coding}/schemas.py.

export type ConsultationStatus =
  | 'uploaded'
  | 'transcribing'
  | 'transcribed'
  | 'extracting'
  | 'extracted'
  | 'coding'
  | 'coded'
  | 'building_fhir'
  | 'pending_review'
  | 'approved'
  | 'rejected'
  | 'submitted'
  | 'failed';

export interface Medication {
  name: string;
  dosage?: string | null;
  frequency?: string | null;
  duration?: string | null;
  route?: string | null;
}

export interface Vital {
  name: string;
  value: string;
  unit?: string | null;
}

export interface ExtractedEntities {
  patient_age?: number | null;
  patient_gender?: string | null;
  chief_complaint?: string | null;
  symptoms: string[];
  duration_of_illness?: string | null;
  vitals: Vital[];
  diagnosis: string[];
  medications: Medication[];
  lab_tests: string[];
  follow_up?: string | null;
  notes?: string | null;
}

export interface CodedDiagnosis {
  term: string;
  icd11_code?: string | null;
  icd11_description?: string | null;
  snomed_code?: string | null;
  snomed_description?: string | null;
}

export interface CodedSymptom {
  term: string;
  snomed_code?: string | null;
  snomed_description?: string | null;
}

export interface CodedMedication {
  name: string;
  rxnorm_code?: string | null;
  rxnorm_description?: string | null;
  generic_name?: string | null;
}

export interface CodingResult {
  diagnoses: CodedDiagnosis[];
  symptoms: CodedSymptom[];
  medications: CodedMedication[];
}

export interface ConsultationListItem {
  consultation_id: string;
  status: ConsultationStatus;
  doctor_name?: string | null;
  transcript_preview?: string | null;
  language?: string | null;
  duration_seconds?: number | null;
  created_at: string;
  updated_at: string;
}

export interface ConsultationDetail {
  consultation_id: string;
  status: ConsultationStatus;
  doctor_name?: string | null;
  transcript?: string | null;
  language?: string | null;
  duration_seconds?: number | null;
  extracted_entities?: ExtractedEntities | null;
  coded_data?: CodingResult | null;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConsultationUploadResponse {
  consultation_id: string;
  status: ConsultationStatus;
  message: string;
  transcript?: string | null;
  language?: string | null;
  duration_seconds?: number | null;
}

export interface FHIRRecordItem {
  id: string;
  resource_type: string;
  resource_json: Record<string, unknown>;
  fhir_server_id?: string | null;
  is_submitted: boolean;
  is_valid: boolean;
  validation_errors?: string | null;
}

export type ApprovalDecision = 'approved' | 'rejected';

export interface ApprovalRequest {
  decision: ApprovalDecision;
  reviewer_id?: string;
  reviewer_name?: string | null;
  notes?: string;
}

export interface ApprovalResponse {
  consultation_id: string;
  decision: ApprovalDecision;
  status: string;
  message: string;
}

export interface ApprovalLogEntry {
  id: string;
  action: string;
  reviewer_id: string;
  reviewer_name?: string | null;
  notes?: string | null;
  created_at: string;
}

export interface ApprovalLogsResponse {
  consultation_id: string;
  current_status: ConsultationStatus;
  logs: ApprovalLogEntry[];
}
