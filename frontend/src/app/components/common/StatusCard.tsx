import type { LucideIcon } from 'lucide-react';

interface StatusCardProps {
  icon: LucideIcon;
  title: string;
  value: string;
  subtitle?: string;
  color?: 'blue' | 'green' | 'orange' | 'purple';
  trend?: {
    value: string;
    label: string;
    positive: boolean;
  };
}

export default function StatusCard({ icon: Icon, title, value, subtitle, color = 'blue', trend }: StatusCardProps) {
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    orange: 'bg-orange-50 text-orange-600',
    purple: 'bg-purple-50 text-purple-600',
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm text-gray-600 mb-1">{title}</p>
          <p className="text-3xl font-semibold text-gray-900 mb-1">{value}</p>
          {subtitle && <p className="text-xs text-gray-500">{subtitle}</p>}
          {trend && (
            <p className={`text-xs mt-2 ${trend.positive ? 'text-green-600' : 'text-red-600'}`}>
              {trend.value} {trend.label}
            </p>
          )}
        </div>
        <div className={`w-12 h-12 rounded-lg ${colorClasses[color]} flex items-center justify-center`}>
          <Icon size={24} />
        </div>
      </div>
    </div>
  );
}
