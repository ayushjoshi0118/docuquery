import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { DocumentItem } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { ConfirmModal } from '../components/ConfirmModal';
import {
  Upload,
  Search,
  Trash2,
  RotateCcw,
  Eye,
  Files,
  Download,
  AlertCircle,
} from 'lucide-react';

interface Props {
  onOpenUpload: () => void;
  onOpenPdf: (documentId: string, pageNumber: number, filename: string) => void;
}

export const DocumentsPage: React.FC<Props> = ({ onOpenUpload, onOpenPdf }) => {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [docToDelete, setDocToDelete] = useState<DocumentItem | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const fetchDocuments = useCallback(async () => {
    try {
      const data = await api.listDocuments(search || undefined);
      setDocuments(data.items);
    } catch (err: any) {
      console.error('Failed to load documents', err);
    } finally {
      setLoading(false);
    }
  }, [search]);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  // Polling mechanism for in-flight documents (queued or processing)
  useEffect(() => {
    const hasInFlight = documents.some((d) => d.status === 'queued' || d.status === 'processing');
    if (!hasInFlight) return;

    const interval = setInterval(() => {
      fetchDocuments();
    }, 3000);

    return () => clearInterval(interval);
  }, [documents, fetchDocuments]);

  const handleRetry = async (doc: DocumentItem) => {
    setActionError(null);
    try {
      const updated = await api.retryDocument(doc.id);
      setDocuments((prev) => prev.map((d) => (d.id === doc.id ? updated : d)));
    } catch (err: any) {
      setActionError(err.message || 'Failed to retry indexing');
    }
  };

  const handleDeleteConfirm = async () => {
    if (!docToDelete) return;
    setDeleting(true);
    setActionError(null);
    try {
      await api.deleteDocument(docToDelete.id);
      setDocuments((prev) => prev.filter((d) => d.id !== docToDelete.id));
      setDocToDelete(null);
    } catch (err: any) {
      setActionError(err.message || 'Failed to delete document');
    } finally {
      setDeleting(false);
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-150">
      {/* Header & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight">Document Library</h1>
          <p className="text-xs text-slate-400 mt-1">
            Manage your uploaded PDF knowledge sources and review indexing states
          </p>
        </div>

        <button
          onClick={onOpenUpload}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-500 transition-colors shadow-lg shadow-emerald-500/20 shrink-0"
        >
          <Upload className="w-4 h-4" />
          Upload PDF
        </button>
      </div>

      {actionError && (
        <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{actionError}</span>
        </div>
      )}

      {/* Search Bar */}
      <div className="relative">
        <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search documents by filename..."
          className="w-full pl-9 pr-4 py-2.5 bg-slate-900 border border-slate-800 rounded-xl text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-emerald-500 transition-colors"
        />
      </div>

      {/* Table view */}
      <div className="border border-slate-800 bg-slate-900/40 rounded-2xl overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-xs text-slate-500">Loading documents...</div>
        ) : documents.length === 0 ? (
          <div className="py-16 text-center">
            <Files className="w-12 h-12 text-slate-600 mx-auto mb-3" />
            <h3 className="text-sm font-semibold text-slate-300">No documents found</h3>
            <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
              {search ? 'Try clearing your search query' : 'Upload your first PDF document to get started'}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900/80 border-b border-slate-800 text-slate-400 font-medium">
                <tr>
                  <th className="py-3 px-4">Filename</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Pages</th>
                  <th className="py-3 px-4">Size</th>
                  <th className="py-3 px-4">Uploaded</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {documents.map((doc) => (
                  <tr key={doc.id} className="hover:bg-slate-900/60 transition-colors">
                    <td className="py-3 px-4 font-medium text-slate-200">
                      <div className="flex items-center gap-2">
                        <Files className="w-4 h-4 text-emerald-400 shrink-0" />
                        <span className="truncate max-w-xs">{doc.filename}</span>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <StatusBadge status={doc.status} errorMessage={doc.error_message} />
                    </td>
                    <td className="py-3 px-4 text-slate-400">{doc.page_count}</td>
                    <td className="py-3 px-4 text-slate-400">{formatBytes(doc.file_size)}</td>
                    <td className="py-3 px-4 text-slate-500">
                      {new Date(doc.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="inline-flex items-center gap-1.5">
                        {doc.status === 'ready' && (
                          <button
                            onClick={() => onOpenPdf(doc.id, 1, doc.filename)}
                            title="View PDF"
                            className="p-1.5 rounded-lg bg-slate-800 text-slate-300 hover:text-emerald-400 hover:bg-slate-700 transition-colors"
                          >
                            <Eye className="w-3.5 h-3.5" />
                          </button>
                        )}

                        <a
                          href={api.getDocumentPdfUrl(doc.id)}
                          download={doc.filename}
                          title="Download PDF"
                          className="p-1.5 rounded-lg bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-700 transition-colors"
                        >
                          <Download className="w-3.5 h-3.5" />
                        </a>

                        {doc.status === 'failed' && (
                          <button
                            onClick={() => handleRetry(doc)}
                            title="Retry indexing"
                            className="p-1.5 rounded-lg bg-amber-500/10 text-amber-400 hover:bg-amber-500/20 transition-colors"
                          >
                            <RotateCcw className="w-3.5 h-3.5" />
                          </button>
                        )}

                        <button
                          onClick={() => setDocToDelete(doc)}
                          title="Delete document"
                          className="p-1.5 rounded-lg bg-slate-800 text-slate-400 hover:text-rose-400 hover:bg-slate-700 transition-colors"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <ConfirmModal
        isOpen={!!docToDelete}
        title="Delete Document"
        message={`Are you sure you want to permanently delete "${docToDelete?.filename}"? All associated vector embeddings and chunks will be deleted.`}
        confirmLabel="Delete permanently"
        loading={deleting}
        onConfirm={handleDeleteConfirm}
        onCancel={() => setDocToDelete(null)}
      />
    </div>
  );
};
