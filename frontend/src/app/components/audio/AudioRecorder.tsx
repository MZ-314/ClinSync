import { useEffect, useRef, useState } from 'react';
import { Mic, Square, PauseCircle, PlayCircle, Upload } from 'lucide-react';

interface AudioRecorderProps {
  onRecordingComplete?: (blob: Blob, mimeType: string, durationSeconds: number) => void;
  onFileSelected?: (file: File) => void;
  isUploading?: boolean;
  disabled?: boolean;
}

export default function AudioRecorder({
  onRecordingComplete,
  onFileSelected,
  isUploading = false,
  disabled = false,
}: AudioRecorderProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [audioLevel, setAudioLevel] = useState(0);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const mimeTypeRef = useRef<string>('audio/webm');
  const streamRef = useRef<MediaStream | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const animationRef = useRef<number | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    return () => {
      stopAllStreams();
      if (timerRef.current) clearInterval(timerRef.current);
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
      if (audioContextRef.current) {
        audioContextRef.current.close().catch(() => undefined);
      }
    };
  }, []);

  const stopAllStreams = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
  };

  const startRecording = async () => {
    if (disabled || isUploading) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const preferred = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4'];
      const supported = preferred.find((t) =>
        typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported(t),
      );
      const mimeType = supported ?? '';
      const recorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream);
      mimeTypeRef.current = recorder.mimeType || 'audio/webm';

      chunksRef.current = [];
      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: mimeTypeRef.current });
        const duration = recordingTimeRef.current;
        chunksRef.current = [];
        if (onRecordingComplete && blob.size > 0) {
          onRecordingComplete(blob, mimeTypeRef.current, duration);
        }
      };

      mediaRecorderRef.current = recorder;
      recorder.start(1000);
      setIsRecording(true);
      setIsPaused(false);
      setRecordingTime(0);
      recordingTimeRef.current = 0;

      timerRef.current = setInterval(() => {
        recordingTimeRef.current += 1;
        setRecordingTime(recordingTimeRef.current);
      }, 1000);

      startAudioLevelMonitor(stream);
    } catch (error) {
      console.error('Error accessing microphone:', error);
      alert('Unable to access microphone. Please check browser permissions.');
    }
  };

  const recordingTimeRef = useRef(0);

  const stopRecording = () => {
    const recorder = mediaRecorderRef.current;
    if (recorder && recorder.state !== 'inactive') {
      try {
        recorder.stop();
      } catch {
        // ignore
      }
    }
    stopAllStreams();
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
      animationRef.current = null;
    }
    setIsRecording(false);
    setIsPaused(false);
    setAudioLevel(0);
  };

  const togglePause = () => {
    const recorder = mediaRecorderRef.current;
    if (!recorder) return;
    if (isPaused) {
      recorder.resume();
      timerRef.current = setInterval(() => {
        recordingTimeRef.current += 1;
        setRecordingTime(recordingTimeRef.current);
      }, 1000);
    } else {
      recorder.pause();
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }
    setIsPaused(!isPaused);
  };

  const startAudioLevelMonitor = (stream: MediaStream) => {
    try {
      const ctx = new AudioContext();
      audioContextRef.current = ctx;
      const analyser = ctx.createAnalyser();
      const source = ctx.createMediaStreamSource(stream);
      source.connect(analyser);
      analyser.fftSize = 256;
      const data = new Uint8Array(analyser.frequencyBinCount);
      const tick = () => {
        analyser.getByteFrequencyData(data);
        let sum = 0;
        for (let i = 0; i < data.length; i++) sum += data[i];
        const avg = sum / data.length;
        setAudioLevel((avg / 255) * 100);
        animationRef.current = requestAnimationFrame(tick);
      };
      tick();
    } catch {
      // Audio level monitoring is non-critical, ignore failures
    }
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file && onFileSelected) {
      onFileSelected(file);
    }
    if (event.target) {
      event.target.value = '';
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const recordDisabled = disabled || isUploading;

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-8">
      <div className="flex flex-col items-center">
        <div
          className={`w-32 h-32 rounded-full flex items-center justify-center mb-6 transition-all ${
            isRecording
              ? 'bg-blue-500 shadow-lg shadow-blue-500/50 animate-pulse'
              : isUploading
              ? 'bg-orange-100'
              : 'bg-gray-100'
          }`}
        >
          <Mic
            size={48}
            className={
              isRecording
                ? 'text-white'
                : isUploading
                ? 'text-orange-500'
                : 'text-gray-400'
            }
          />
        </div>

        {isRecording && (
          <div className="w-full mb-6">
            <div className="flex items-center justify-center gap-1 h-16">
              {[...Array(40)].map((_, i) => (
                <div
                  key={i}
                  className="w-1 bg-blue-500 rounded-full transition-all"
                  style={{
                    height: `${Math.random() * audioLevel + 10}%`,
                    opacity: 0.5 + audioLevel / 200,
                  }}
                />
              ))}
            </div>
          </div>
        )}

        <div className="text-center mb-6">
          <p className="text-3xl font-semibold text-gray-900 mb-2">
            {formatTime(recordingTime)}
          </p>
          <p className="text-sm text-gray-500">
            {isUploading
              ? 'Uploading & transcribing…'
              : isRecording
              ? isPaused
                ? 'Recording Paused'
                : 'Recording in Progress'
              : 'Ready to Record'}
          </p>
        </div>

        <div className="flex flex-wrap justify-center gap-3">
          {!isRecording ? (
            <>
              <button
                onClick={startRecording}
                disabled={recordDisabled}
                className="px-8 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2 font-medium disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Mic size={20} />
                Start Recording
              </button>
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={recordDisabled}
                className="px-6 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors flex items-center gap-2 font-medium disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Upload size={20} />
                Upload Audio File
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept="audio/*,video/webm"
                className="hidden"
                onChange={handleFileChange}
              />
            </>
          ) : (
            <>
              <button
                onClick={togglePause}
                className="px-6 py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors flex items-center gap-2"
              >
                {isPaused ? <PlayCircle size={20} /> : <PauseCircle size={20} />}
                {isPaused ? 'Resume' : 'Pause'}
              </button>
              <button
                onClick={stopRecording}
                className="px-6 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors flex items-center gap-2"
              >
                <Square size={20} />
                Stop & Submit
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
