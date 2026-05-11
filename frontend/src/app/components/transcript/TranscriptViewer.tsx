import { Clock, User } from 'lucide-react';

interface TranscriptEntry {
  speaker: string;
  text: string;
  timestamp: number;
}

interface TranscriptViewerProps {
  transcript?: TranscriptEntry[];
}

export default function TranscriptViewer({ transcript = [] }: TranscriptViewerProps) {
  const formatTimestamp = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200">
      <div className="p-4 border-b border-gray-200">
        <h3 className="font-medium text-gray-900">Live Transcription</h3>
      </div>

      <div className="p-4 space-y-4 max-h-[600px] overflow-y-auto">
        {transcript.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-500">Start recording to see live transcription</p>
          </div>
        ) : (
          transcript.map((entry, index) => (
            <div key={index} className="flex gap-4">
              <div className="flex flex-col items-center">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                  entry.speaker === 'Doctor' ? 'bg-blue-100 text-blue-600' : 'bg-green-100 text-green-600'
                }`}>
                  <User size={16} />
                </div>
                <div className="flex items-center gap-1 mt-1 text-xs text-gray-500">
                  <Clock size={12} />
                  <span>{formatTimestamp(entry.timestamp)}</span>
                </div>
              </div>

              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900 mb-1">{entry.speaker}</p>
                <p className="text-sm text-gray-700 leading-relaxed">{entry.text}</p>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
