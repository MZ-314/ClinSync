import { Edit2, AlertCircle } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import Badge from '../common/Badge';

interface Entity {
  value: string;
  confidence: number;
}

interface EntityCardProps {
  title: string;
  entities?: Entity[];
  icon: LucideIcon;
  color?: 'blue' | 'green' | 'orange' | 'purple' | 'red';
}

export default function EntityCard({ title, entities = [], icon: Icon, color = 'blue' }: EntityCardProps) {
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    orange: 'bg-orange-50 text-orange-600',
    purple: 'bg-purple-50 text-purple-600',
    red: 'bg-red-50 text-red-600',
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="flex items-center gap-3 mb-4">
        <div className={`w-10 h-10 rounded-lg ${colorClasses[color]} flex items-center justify-center`}>
          <Icon size={20} />
        </div>
        <div>
          <h3 className="font-medium text-gray-900">{title}</h3>
          <p className="text-xs text-gray-500">{entities.length} items extracted</p>
        </div>
      </div>

      <div className="space-y-3">
        {entities.map((entity, index) => (
          <div key={index} className="p-4 bg-gray-50 rounded-lg group hover:bg-gray-100 transition-colors">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900 mb-2">{entity.value}</p>
                <div className="flex items-center gap-2">
                  <Badge variant={entity.confidence >= 0.8 ? 'success' : 'warning'} size="sm">
                    {Math.round(entity.confidence * 100)}% confidence
                  </Badge>
                  {entity.confidence < 0.8 && (
                    <div className="flex items-center gap-1 text-xs text-orange-600">
                      <AlertCircle size={12} />
                      <span>Needs review</span>
                    </div>
                  )}
                </div>
              </div>
              <button className="opacity-0 group-hover:opacity-100 transition-opacity p-2 hover:bg-white rounded">
                <Edit2 size={16} className="text-gray-600" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
