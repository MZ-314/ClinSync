import Badge from '../common/Badge';
import { AlertCircle, CheckCircle, Clock } from 'lucide-react';

interface MedicalCode {
  term: string;
  description: string;
  system: string;
  code: string;
  confidence: number;
  status: 'mapped' | 'pending' | 'failed';
}

interface CodingTableProps {
  codes?: MedicalCode[];
}

export default function CodingTable({ codes = [] }: CodingTableProps) {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'mapped':
        return <CheckCircle size={16} className="text-green-600" />;
      case 'pending':
        return <Clock size={16} className="text-orange-600" />;
      case 'failed':
        return <AlertCircle size={16} className="text-red-600" />;
      default:
        return null;
    }
  };

  const getStatusVariant = (status: string): 'success' | 'warning' | 'error' | 'default' => {
    switch (status) {
      case 'mapped':
        return 'success';
      case 'pending':
        return 'warning';
      case 'failed':
        return 'error';
      default:
        return 'default';
    }
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <table className="w-full">
        <thead className="bg-gray-50 border-b border-gray-200">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Clinical Term</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Code System</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Code</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Confidence</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {codes.map((code, index) => (
            <tr key={index} className="hover:bg-gray-50">
              <td className="px-6 py-4">
                <p className="text-sm font-medium text-gray-900">{code.term}</p>
                <p className="text-xs text-gray-500 mt-1">{code.description}</p>
              </td>
              <td className="px-6 py-4">
                <Badge variant="info" size="sm">{code.system}</Badge>
              </td>
              <td className="px-6 py-4">
                <code className="text-sm text-gray-900 bg-gray-100 px-2 py-1 rounded">
                  {code.code}
                </code>
              </td>
              <td className="px-6 py-4">
                <div className="flex items-center gap-2">
                  <div className="flex-1 bg-gray-200 rounded-full h-2 max-w-[100px]">
                    <div
                      className={`h-2 rounded-full ${
                        code.confidence >= 0.8 ? 'bg-green-500' : code.confidence >= 0.6 ? 'bg-orange-500' : 'bg-red-500'
                      }`}
                      style={{ width: `${code.confidence * 100}%` }}
                    ></div>
                  </div>
                  <span className="text-sm text-gray-600">{Math.round(code.confidence * 100)}%</span>
                </div>
              </td>
              <td className="px-6 py-4">
                <div className="flex items-center gap-2">
                  {getStatusIcon(code.status)}
                  <Badge variant={getStatusVariant(code.status)} size="sm">
                    {code.status}
                  </Badge>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
