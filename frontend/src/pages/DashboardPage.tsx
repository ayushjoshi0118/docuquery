import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { SystemStats, DocumentItem } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import {
  Files,
  CheckCircle2,
  BookOpen,
  MessageSquare,
  HardDrive,
  Upload,
  ArrowRight,
  Sparkles,
} from 'lucide-react';

interface Props {
  onNavigate: (tab: string) => void;
  onOpenUpload: () => void;
  onOpenPdf: (documentId: string, pageNumber: number, filename: string) => void;
}

export const DashboardPage: React.FC<Props> = ({ onNavigate, onOpenUpload, onOpenPdf }) => {
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [recentDocs, setRecentDocs] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadDashboardData = async () => {
      try {
        const [statsData, docsData] = await Promise.all([
          api.getStats(),
          api.listDocuments(undefined, 5, 0),
        ]);
        setStats(statsData);
        setRecentDocs(docsData.items);
      } catch (err) {
        console.error('Failed to load dashboard data', err);
      } finally {
        setLoading(false);
      }
    };
    loadDashboardData();
  }, []);

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-150">
      {/* Hero Welcome banner */}
      <div className="relative overflow-hidden rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 via-slate-900 to-emerald-950/30 p-8">
        <div className="relative z-10 max-w-2xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold mb-4">
            <Sparkles className="w-3.5 h-3.5" />
            AI Document Intelligence
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight sm:text-3xl">
            Welcome to DocuQuery
          </h1>
          <p className="mt-2 text-sm text-slate-400 leading-relaxed">
            Upload PDF documents for private vector indexing and natural-language Q&A. Answers are strictly grounded in your documents with page-level citations.
          </p>

          <div className="mt-6 flex flex-wrap items-center gap-3">
            <button
              onClick={onOpenUpload}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-500 transition-colors shadow-lg shadow-emerald-500/20"
            >
              <Upload className="w-4 h-4" />
              Upload PDF
            </button>
            <button
              onClick={() => onNavigate('chat')}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold text-slate-200 bg-slate-800 hover:bg-slate-700 border border-slate-700 transition-colors"
            >
              <MessageSquare className="w-4 h-4 text-emerald-400" />
              Start New Query
            </button>
          </div>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/60">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">Total Documents</span>
            <Files className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-white">
            {loading ? '—' : stats?.total_documents ?? 0}
          </div>
        </div>

        <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/60">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">Ready Documents</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400">
            {loading ? '—' : stats?.ready_documents ?? 0}
          </div>
        </div>

        <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/60">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">Pages Indexed</span>
            <BookOpen className="w-4 h-4 text-teal-400" />
          </div>
          <div className="text-2xl font-bold text-white">
            {loading ? '—' : stats?.total_pages ?? 0}
          </div>
        </div>

        <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/60">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">AI Queries Run</span>
            <MessageSquare className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-white">
            {loading ? '—' : stats?.total_queries ?? 0}
          </div>
        </div>

        <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/60 col-span-2 lg:col-span-1">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">Storage Used</span>
            <HardDrive className="w-4 h-4 text-slate-400" />
          </div>
          <div className="text-2xl font-bold text-white">
            {loading ? '—' : formatBytes(stats?.storage_used_bytes ?? 0)}
          </div>
        </div>
      </div>

      {/* Recent Documents Section */}
      <div className="border border-slate-800 bg-slate-900/40 rounded-2xl p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-base font-semibold text-white">Recent Documents</h2>
            <p className="text-xs text-slate-400">Your latest uploaded knowledge sources</p>
          </div>
          <button
            onClick={() => onNavigate('documents')}
            className="inline-flex items-center gap-1.5 text-xs font-medium text-emerald-400 hover:text-emerald-300"
          >
            View all
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {recentDocs.length === 0 ? (
          <div className="py-12 text-center">
            <Files className="w-10 h-10 text-slate-600 mx-auto mb-3" />
            <h3 className="text-sm font-medium text-slate-300">No documents uploaded yet</h3>
            <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
              Upload PDF manuals, reports, or research papers to begin asking questions.
            </p>
            <button
              onClick={onOpenUpload}
              className="mt-4 px-4 py-2 rounded-xl text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-500 transition-colors inline-flex items-center gap-2"
            >
              <Upload className="w-3.5 h-3.5" />
              Upload First PDF
            </button>
          </div>
        ) : (
          <div className="divide-y divide-slate-800/60">
            {recentDocs.map((doc) => (
              <div
                key={doc.id}
                className="py-3 flex items-center justify-between gap-4 hover:bg-slate-900/60 px-2 rounded-lg transition-colors"
              >
                <div className="flex items-center gap-3 overflow-hidden">
                  <div className="p-2 rounded-lg bg-slate-800 text-slate-300">
                    <Files className="w-4 h-4 text-emerald-400" />
                  </div>
                  <div className="overflow-hidden">
                    <button
                      onClick={() => onOpenPdf(doc.id, 1, doc.filename)}
                      className="text-xs font-semibold text-slate-200 hover:text-emerald-400 truncate block text-left"
                    >
                      {doc.filename}
                    </button>
                    <p className="text-[11px] text-slate-500">
                      {doc.page_count} {doc.page_count === 1 ? 'page' : 'pages'} • {formatBytes(doc.file_size)} • {new Date(doc.created_at).toLocaleDateString()}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3 shrink-0">
                  <StatusBadge status={doc.status} errorMessage={doc.error_message} />
                  <button
                    onClick={() => onOpenPdf(doc.id, 1, doc.filename)}
                    className="text-xs text-slate-400 hover:text-slate-200 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 transition-colors"
                  >
                    View
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
