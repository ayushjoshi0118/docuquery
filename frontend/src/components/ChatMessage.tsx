import React from 'react';
import { Message } from '../types';
import { CitationCard } from './CitationCard';
import { User, Sparkles, BookOpen } from 'lucide-react';

interface Props {
  message: Message;
  onOpenPdf: (documentId: string, pageNumber: number, filename: string) => void;
}

export const ChatMessage: React.FC<Props> = ({ message, onOpenPdf }) => {
  const isUser = message.role === 'user';

  return (
    <div className={`flex gap-4 p-4 rounded-xl ${isUser ? 'bg-slate-900/40' : 'bg-slate-900/80 border border-slate-800/80'}`}>
      <div className="shrink-0">
        {isUser ? (
          <div className="w-8 h-8 rounded-lg bg-slate-800 text-slate-300 flex items-center justify-center font-medium text-xs border border-slate-700">
            <User className="w-4 h-4" />
          </div>
        ) : (
          <div className="w-8 h-8 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center font-medium text-xs border border-emerald-500/20 shadow-sm shadow-emerald-500/10">
            <Sparkles className="w-4 h-4" />
          </div>
        )}
      </div>

      <div className="flex-1 space-y-3 overflow-hidden">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-slate-200">
            {isUser ? 'You' : 'DocuQuery AI'}
          </span>
          <span className="text-[10px] text-slate-500">
            {new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        </div>

        <div className="text-sm text-slate-200 leading-relaxed whitespace-pre-wrap">
          {message.content}
        </div>

        {/* Citations shelf */}
        {message.citations && message.citations.length > 0 && (
          <div className="mt-4 pt-3 border-t border-slate-800/80">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-400 mb-2">
              <BookOpen className="w-3.5 h-3.5 text-emerald-400" />
              <span>Grounded Sources ({message.citations.length})</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {message.citations.map((c, idx) => (
                <CitationCard
                  key={c.chunk_id || `${c.document_id}-${c.page_number}-${idx}`}
                  citation={c}
                  onOpenPdf={onOpenPdf}
                />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
