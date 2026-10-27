import React, { useState } from 'react';
import { useAuth } from './context/AuthContext';
import { Layout } from './components/Layout';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { DashboardPage } from './pages/DashboardPage';
import { DocumentsPage } from './pages/DocumentsPage';
import { ChatPage } from './pages/ChatPage';
import { SettingsPage } from './pages/SettingsPage';
import { PdfViewerModal } from './components/PdfViewerModal';
import { DocumentUploadModal } from './components/DocumentUploadModal';
import { Loader2 } from 'lucide-react';

export const AppContent: React.FC = () => {
  const { user, loading } = useAuth();
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
  const [activeTab, setActiveTab] = useState<string>('dashboard');

  // PDF Viewer Modal State
  const [pdfModalOpen, setPdfModalOpen] = useState(false);
  const [pdfDocId, setPdfDocId] = useState('');
  const [pdfFilename, setPdfFilename] = useState('');
  const [pdfPage, setPdfPage] = useState(1);

  // Upload Modal State
  const [uploadModalOpen, setUploadModalOpen] = useState(false);

  const handleOpenPdf = (documentId: string, pageNumber: number, filename: string) => {
    setPdfDocId(documentId);
    setPdfPage(pageNumber);
    setPdfFilename(filename);
    setPdfModalOpen(true);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center text-slate-400 gap-3">
        <Loader2 className="w-8 h-8 animate-spin text-emerald-500" />
        <span className="text-xs font-medium">Initializing DocuQuery...</span>
      </div>
    );
  }

  if (!user) {
    return authMode === 'login' ? (
      <LoginPage onSwitchToRegister={() => setAuthMode('register')} />
    ) : (
      <RegisterPage onSwitchToLogin={() => setAuthMode('login')} />
    );
  }

  return (
    <Layout activeTab={activeTab} setActiveTab={setActiveTab}>
      {activeTab === 'dashboard' && (
        <DashboardPage
          onNavigate={setActiveTab}
          onOpenUpload={() => setUploadModalOpen(true)}
          onOpenPdf={handleOpenPdf}
        />
      )}
      {activeTab === 'documents' && (
        <DocumentsPage
          onOpenUpload={() => setUploadModalOpen(true)}
          onOpenPdf={handleOpenPdf}
        />
      )}
      {activeTab === 'chat' && (
        <ChatPage onOpenPdf={handleOpenPdf} />
      )}
      {activeTab === 'settings' && (
        <SettingsPage />
      )}

      {/* Global Modals */}
      <PdfViewerModal
        isOpen={pdfModalOpen}
        onClose={() => setPdfModalOpen(false)}
        documentId={pdfDocId}
        filename={pdfFilename}
        initialPageNumber={pdfPage}
      />

      <DocumentUploadModal
        isOpen={uploadModalOpen}
        onClose={() => setUploadModalOpen(false)}
        onUploaded={() => {
          // Refresh tab if on documents
          if (activeTab === 'dashboard') {
            setActiveTab('documents');
          }
        }}
      />
    </Layout>
  );
};

export const App: React.FC = () => {
  return <AppContent />;
};

export default App;
