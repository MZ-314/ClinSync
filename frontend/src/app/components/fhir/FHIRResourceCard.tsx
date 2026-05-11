import { useState } from 'react';
import { ChevronDown, ChevronRight, CheckCircle, AlertCircle } from 'lucide-react';
import Badge from '../common/Badge';

interface FHIRResource {
  resourceType: string;
  id: string;
  valid: boolean;
  data: Record<string, unknown>;
}

interface FHIRResourceCardProps {
  resource: FHIRResource;
}

export default function FHIRResourceCard({ resource }: FHIRResourceCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="bg-white rounded-lg border border-gray-200">
      <div
        className="p-4 flex items-center justify-between cursor-pointer hover:bg-gray-50"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-3">
          {isExpanded ? <ChevronDown size={20} /> : <ChevronRight size={20} />}
          <div>
            <h3 className="font-medium text-gray-900">{resource.resourceType}</h3>
            <p className="text-sm text-gray-500">ID: {resource.id}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={resource.valid ? 'success' : 'warning'}>
            {resource.valid ? 'Valid' : 'Needs Review'}
          </Badge>
          {resource.valid ? (
            <CheckCircle size={20} className="text-green-600" />
          ) : (
            <AlertCircle size={20} className="text-orange-600" />
          )}
        </div>
      </div>

      {isExpanded && (
        <div className="border-t border-gray-200 p-4 bg-gray-50">
          <pre className="text-xs text-gray-700 overflow-x-auto bg-white p-4 rounded border border-gray-200">
            {JSON.stringify(resource.data, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
