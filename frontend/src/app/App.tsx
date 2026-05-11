import { BrowserRouter, Routes, Route } from 'react-router';
import { Toaster } from 'sonner';
import Sidebar from './components/layout/Sidebar';
import Navbar from './components/layout/Navbar';
import Dashboard from './pages/Dashboard';
import LiveConsultation from './pages/LiveConsultation';
import TranscriptReview from './pages/TranscriptReview';
import ClinicalEntities from './pages/ClinicalEntities';
import MedicalCoding from './pages/MedicalCoding';
import FHIRViewer from './pages/FHIRViewer';
import ApprovalDashboard from './pages/ApprovalDashboard';

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen bg-gray-50">
        <Sidebar />
        <div className="flex-1 flex flex-col overflow-hidden">
          <Navbar />
          <main className="flex-1 overflow-y-auto">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/live-consultation" element={<LiveConsultation />} />
              <Route path="/transcript-review" element={<TranscriptReview />} />
              <Route path="/transcript-review/:id" element={<TranscriptReview />} />
              <Route path="/clinical-entities" element={<ClinicalEntities />} />
              <Route path="/clinical-entities/:id" element={<ClinicalEntities />} />
              <Route path="/medical-coding" element={<MedicalCoding />} />
              <Route path="/medical-coding/:id" element={<MedicalCoding />} />
              <Route path="/fhir-viewer" element={<FHIRViewer />} />
              <Route path="/fhir-viewer/:id" element={<FHIRViewer />} />
              <Route path="/approval-dashboard" element={<ApprovalDashboard />} />
              <Route path="/approval-dashboard/:id" element={<ApprovalDashboard />} />
            </Routes>
          </main>
        </div>
        <Toaster position="top-right" />
      </div>
    </BrowserRouter>
  );
}
