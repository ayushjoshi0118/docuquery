import React from 'react';
import { Citation } from '../types';
import { FileText, ExternalLink } from 'lucide-react';

interface Props {
  citation: Citation;
  onOpenPdf: (documentId: string, pageNumber: number, filename: string) => void;
}

export const CitationCard: React.FC<Props> = ({ citation, onOpenPdf }) => {
  return (
    <div
      onClick={() => onOpenPdf(citation.document_id, citation.page_number, citation.filename)}
      className="group flex flex-col p-2.5 rounded-lg border border-slate-800 bg-slate-900/60 hover:bg-slate-800/80 hover:border-emerald-500/40 cursor-pointer transition-all duration-150 text-left"
    >
      <div className="flex items-center justify-between gap-2 mb-1">
        <div className="flex items-center gap-1.5 overflow-hidden">
          <FileText className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
          <span className="text-xs font-semibold text-slate-200 truncate group-hover:text-emerald-300">
            {citation.filename}
          </span>
        </div>
        <span className="inline-flex items-center gap-1 text-[11px] font-mono text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20 shrink-0">
          p. {citation.page_number}
          <ExternalLink className="w-2.5 h-2.5 opacity-60 group-hover:opacity-100" />
        </span>
      </div>
      <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed italic">
        "{citation.excerpt}"
      </p>
    </div>
  );
};
