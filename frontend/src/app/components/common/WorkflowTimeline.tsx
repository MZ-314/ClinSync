import { Mic, FileText, Brain, Code, Database, UserCheck, Send, Check } from 'lucide-react';

export default function WorkflowTimeline({ currentStep = 1 }: { currentStep?: number }) {
  const steps = [
    { icon: Mic, label: 'Audio Capture', step: 1 },
    { icon: FileText, label: 'Transcription', step: 2 },
    { icon: Brain, label: 'Entity Extraction', step: 3 },
    { icon: Code, label: 'Medical Coding', step: 4 },
    { icon: Database, label: 'FHIR Generation', step: 5 },
    { icon: UserCheck, label: 'Doctor Approval', step: 6 },
    { icon: Send, label: 'FHIR Submission', step: 7 },
  ];

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="flex items-center justify-between">
        {steps.map((item, index) => {
          const Icon = item.icon;
          const isCompleted = currentStep > item.step;
          const isActive = currentStep === item.step;

          return (
            <div key={item.step} className="flex items-center flex-1">
              <div className="flex flex-col items-center">
                <div
                  className={`w-12 h-12 rounded-full flex items-center justify-center ${
                    isCompleted
                      ? 'bg-green-100 text-green-600'
                      : isActive
                      ? 'bg-blue-100 text-blue-600 ring-4 ring-blue-50'
                      : 'bg-gray-100 text-gray-400'
                  }`}
                >
                  {isCompleted ? <Check size={20} /> : <Icon size={20} />}
                </div>
                <p className={`text-xs mt-2 text-center ${
                  isActive ? 'text-blue-600 font-medium' : 'text-gray-600'
                }`}>
                  {item.label}
                </p>
              </div>

              {index < steps.length - 1 && (
                <div className={`flex-1 h-1 mx-2 ${
                  isCompleted ? 'bg-green-300' : 'bg-gray-200'
                }`}></div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
