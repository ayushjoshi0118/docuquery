import React, { useState, useEffect } from 'react';
import { X, Download, FileText, ChevronLeft, ChevronRight } from 'lucide-react';
import { api } from '../api/client';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  documentId: string;
  filename: string;
  initialPageNumber?: number;
}

export const PdfViewerModal: React.FC<Props> = ({
  isOpen,
  onClose,
  documentId,
  filename,
  initialPageNumber = 1,
}) => {
  const [currentPage, setCurrentPage] = useState<number>(initialPageNumber);

  useEffect(() => {
    setCurrentPage(initialPageNumber);
  }, [initialPageNumber, documentId]);

  if (!isOpen) return null;

  const pdfUrl = `${api.getDocumentPdfUrl(documentId)}#page=${currentPage}`;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="flex flex-col w-full max-w-5xl h-[90vh] bg-slate-900 border border-slate-800 rounded-xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/90">
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-100 truncate">{filename}</h3>
              <p className="text-xs text-slate-400">Navigating cited page {currentPage}</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Page Controls */}
            <div className="flex items-center gap-1.5 bg-slate-800 px-2.5 py-1 rounded-lg border border-slate-700 text-xs">
              <button
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={currentPage <= 1}
                title="Previous page"
                className="p-0.5 text-slate-300 hover:text-white disabled:opacity-30 disabled:hover:text-slate-300"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="font-mono text-xs text-slate-200 px-1">Page {currentPage}</span>
              <button
                onClick={() => setCurrentPage((p) => p + 1)}
                title="Next page"
                className="p-0.5 text-slate-300 hover:text-white"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>

            <a
              href={api.getDocumentPdfUrl(documentId)}
              target="_blank"
              rel="noreferrer"
              download={filename}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              Download
            </a>

            <button
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-slate-100 hover:bg-slate-800 rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* PDF viewer frame */}
        <div className="flex-1 w-full bg-slate-950 relative">
          <iframe
            key={`${documentId}-${currentPage}`}
            src={pdfUrl}
            title={filename}
            className="w-full h-full border-none"
          />
        </div>
      </div>
    </div>
  );
};
