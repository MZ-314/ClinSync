import { useState } from 'react';
import { useNavigate } from 'react-router';
import { toast } from 'sonner';
import { Brain, AlertTriangle, Loader } from 'lucide-react';

import AudioRecorder from '../components/audio/AudioRecorder';
import TranscriptViewer from '../components/transcript/TranscriptViewer';
import WorkflowTimeline from '../components/common/WorkflowTimeline';
import Badge from '../components/common/Badge';
import { ApiError, uploadConsultation } from '../lib/api';
import { statusLabel, statusToWorkflowStep } from '../lib/hooks';
import type { ConsultationUploadResponse } from '../lib/types';

export default function LiveConsultation() {
  const navigate = useNavigate();
  const [uploading, setUploading] = useState(false);
  const [response, setResponse] = useState<ConsultationUploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleUpload = async (blob: Blob, mimeType: string) => {
    if (!blob.size) {
      setError('Recording was empty. Please try again.');
      return;
    }
    setError(null);
    setUploading(true);
    setResponse(null);
    try {
      const extMap: Record<string, string> = {
        'audio/webm': 'webm',
        'audio/webm;codecs=opus': 'webm',
        'audio/mp4': 'm4a',
        'audio/mpeg': 'mp3',
        'audio/wav': 'wav',
        'audio/ogg': 'ogg',
      };
      const ext = extMap[mimeType] ?? 'webm';
      const result = await uploadConsultation(blob, {
        filename: `consultation-${Date.now()}.${ext}`,
      });
      setResponse(result);
      toast.success('Audio uploaded and transcribed. Continue to review.');
      // Auto-navigate after a brief delay so the user sees the transcript preview.
      setTimeout(() => {
        navigate(`/transcript-review/${result.consultation_id}`);
      }, 1200);
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
          ? err.message
          : 'Upload failed.';
      setError(message);
      toast.error(message);
    } finally {
      setUploading(false);
    }
  };

  const handleFileSelected = async (file: File) => {
    await handleUpload(file, file.type || 'audio/webm');
  };

  const transcriptForView = response?.transcript
    ? [
        {
          speaker: 'Transcript',
          text: response.transcript,
          timestamp: 0,
        },
      ]
    : [];

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Live Consultation</h1>
        <p className="text-sm text-gray-600 mt-1">
          Record or upload a consultation audio and run the documentation pipeline
        </p>
      </div>

      <WorkflowTimeline
        currentStep={response ? statusToWorkflowStep(response.status) : 1}
      />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-6">
          <AudioRecorder
            onRecordingComplete={handleUpload}
            onFileSelected={handleFileSelected}
            isUploading={uploading}
          />

          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <div className="flex items-center gap-3 mb-4">
              <Brain className="text-blue-600" size={24} />
              <div>
                <h3 className="font-medium text-gray-900">Pipeline Status</h3>
                <p className="text-sm text-gray-600">
                  After upload, transcription runs synchronously and the rest of
                  the pipeline runs in the background.
                </p>
              </div>
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <span className="text-sm text-gray-700">Transcription</span>
                {uploading ? (
                  <div className="flex items-center gap-2">
                    <Loader size={16} className="text-blue-600 animate-spin" />
                    <Badge variant="info" size="sm">In Progress</Badge>
                  </div>
                ) : response ? (
                  <Badge variant="success" size="sm">Complete</Badge>
                ) : (
                  <Badge variant="default" size="sm">Idle</Badge>
                )}
              </div>

              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <span className="text-sm text-gray-700">Current Status</span>
                <Badge variant={response ? 'info' : 'default'} size="sm">
                  {response ? statusLabel(response.status) : 'Awaiting upload'}
                </Badge>
              </div>
            </div>

            {error && (
              <div className="mt-4 flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-lg">
                <AlertTriangle size={16} className="text-red-600 mt-0.5 flex-shrink-0" />
                <p className="text-sm text-red-700">{error}</p>
              </div>
            )}
          </div>
        </div>

        <div>
          <TranscriptViewer transcript={transcriptForView} />
        </div>
      </div>

      <div className="bg-blue-50 rounded-lg p-6 border border-blue-200">
        <h3 className="font-medium text-blue-900 mb-2">Recording Guidelines</h3>
        <ul className="text-sm text-blue-700 space-y-1">
          <li>• Allow microphone access when prompted by the browser.</li>
          <li>• Speak clearly and minimise background noise.</li>
          <li>• Supported formats: WebM, MP3, M4A, WAV, OGG, FLAC.</li>
          <li>• After upload you will be redirected to the Transcript Review.</li>
        </ul>
      </div>
    </div>
  );
}
