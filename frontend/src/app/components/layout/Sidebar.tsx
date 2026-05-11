import { Activity, FileText, Stethoscope, Code, Database, CheckSquare, LayoutDashboard } from 'lucide-react';
import { Link, useLocation } from 'react-router';

export default function Sidebar() {
  const location = useLocation();

  const menuItems = [
    { icon: LayoutDashboard, label: 'Dashboard', path: '/' },
    { icon: Activity, label: 'Live Consultation', path: '/live-consultation' },
    { icon: FileText, label: 'Transcript Review', path: '/transcript-review' },
    { icon: Stethoscope, label: 'Clinical Entities', path: '/clinical-entities' },
    { icon: Code, label: 'Medical Coding', path: '/medical-coding' },
    { icon: Database, label: 'FHIR Viewer', path: '/fhir-viewer' },
    { icon: CheckSquare, label: 'Approval Dashboard', path: '/approval-dashboard' },
  ];

  return (
    <div className="w-64 bg-white border-r border-gray-200 h-screen flex flex-col">
      <div className="p-6 border-b border-gray-200">
        <h1 className="text-xl font-semibold text-blue-600">CareGraph AI</h1>
        <p className="text-xs text-gray-500 mt-1">Clinical Documentation System</p>
      </div>

      <nav className="flex-1 p-4 space-y-1">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = location.pathname === item.path;

          return (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                isActive
                  ? 'bg-blue-50 text-blue-600'
                  : 'text-gray-700 hover:bg-gray-50'
              }`}
            >
              <Icon size={20} />
              <span className="text-sm font-medium">{item.label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-gray-200">
        <div className="px-4 py-3 bg-blue-50 rounded-lg">
          <p className="text-xs font-medium text-blue-900">System Status</p>
          <p className="text-xs text-blue-600 mt-1">All systems operational</p>
        </div>
      </div>
    </div>
  );
}
