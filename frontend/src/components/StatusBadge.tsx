import React from 'react';
import { DocumentStatus } from '../types';
import { CheckCircle2, Clock, AlertCircle, Loader2 } from 'lucide-react';

interface Props {
  status: DocumentStatus;
  errorMessage?: string | null;
}

export const StatusBadge: React.FC<Props> = ({ status, errorMessage }) => {
  switch (status) {
    case 'ready':
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
          Ready
        </span>
      );
    case 'processing':
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20">
          <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-400" />
          Indexing...
        </span>
      );
    case 'queued':
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
          <Clock className="w-3.5 h-3.5 text-amber-400" />
          Queued
        </span>
      );
    case 'failed':
      return (
        <span
          title={errorMessage || 'Indexing failed'}
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20 cursor-help"
        >
          <AlertCircle className="w-3.5 h-3.5 text-rose-400" />
          Failed
        </span>
      );
    default:
      return null;
  }
};
