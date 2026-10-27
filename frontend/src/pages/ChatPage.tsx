import React, { useState, useEffect, useRef } from 'react';
import { api } from '../api/client';
import { Conversation, Message, DocumentItem } from '../types';
import { ChatMessage } from '../components/ChatMessage';
import {
  MessageSquare,
  Plus,
  Send,
  Trash2,
  Edit2,
  Check,
  X,
  Filter,
  Sparkles,
  Loader2,
  AlertCircle,
} from 'lucide-react';

interface Props {
  onOpenPdf: (documentId: string, pageNumber: number, filename: string) => void;
}

export const ChatPage: React.FC<Props> = ({ onOpenPdf }) => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [readyDocs, setReadyDocs] = useState<DocumentItem[]>([]);
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [question, setQuestion] = useState('');
  const [loadingConv, setLoadingConv] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Rename states
  const [editingConvId, setEditingConvId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load conversations & ready docs
  useEffect(() => {
    const init = async () => {
      try {
        const [convList, docList] = await Promise.all([
          api.listConversations(),
          api.listDocuments(undefined, 100, 0),
        ]);
        setConversations(convList);
        setReadyDocs(docList.items.filter((d) => d.status === 'ready'));

        if (convList.length > 0) {
          setActiveConversationId(convList[0].id);
        } else {
          // Auto create initial conversation
          const newConv = await api.createConversation('General Q&A');
          setConversations([newConv]);
          setActiveConversationId(newConv.id);
        }
      } catch (err: any) {
        setError(err.message || 'Failed to initialize chat');
      } finally {
        setLoadingConv(false);
      }
    };
    init();
  }, []);

  // Load messages whenever activeConversationId changes
  useEffect(() => {
    if (!activeConversationId) return;

    const loadMessages = async () => {
      try {
        const detail = await api.getConversation(activeConversationId);
        setMessages(detail.messages);
      } catch (err: any) {
        setError(err.message || 'Failed to load conversation history');
      }
    };
    loadMessages();
  }, [activeConversationId]);

  // Scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, submitting]);

  const handleCreateConversation = async () => {
    try {
      const newConv = await api.createConversation('New Conversation');
      setConversations((prev) => [newConv, ...prev]);
      setActiveConversationId(newConv.id);
      setMessages([]);
    } catch (err: any) {
      setError(err.message || 'Failed to create conversation');
    }
  };

  const handleDeleteConversation = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await api.deleteConversation(id);
      const remaining = conversations.filter((c) => c.id !== id);
      setConversations(remaining);
      if (activeConversationId === id) {
        if (remaining.length > 0) {
          setActiveConversationId(remaining[0].id);
        } else {
          handleCreateConversation();
        }
      }
    } catch (err: any) {
      setError(err.message || 'Failed to delete conversation');
    }
  };

  const handleStartRename = (conv: Conversation, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingConvId(conv.id);
    setEditTitle(conv.title);
  };

  const handleSaveRename = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!editTitle.trim()) return;
    try {
      const updated = await api.renameConversation(id, editTitle.trim());
      setConversations((prev) => prev.map((c) => (c.id === id ? { ...c, title: updated.title } : c)));
      setEditingConvId(null);
    } catch (err: any) {
      setError(err.message || 'Failed to rename conversation');
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim() || !activeConversationId || submitting) return;

    const currentQ = question.trim();
    setQuestion('');
    setSubmitting(true);
    setError(null);

    // Optimistic user message
    const tempUserMsg: Message = {
      id: `temp-${Date.now()}`,
      conversation_id: activeConversationId,
      role: 'user',
      content: currentQ,
      citations: null,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      const response = await api.sendMessage(
        activeConversationId,
        currentQ,
        selectedDocIds.length > 0 ? selectedDocIds : undefined
      );

      // Replace optimistic message and append assistant message
      setMessages((prev) => [
        ...prev.filter((m) => m.id !== tempUserMsg.id),
        response.user_message,
        response.assistant_message,
      ]);

      // Update conversation title in list if it was New Conversation
      setConversations((prev) =>
        prev.map((c) => {
          if (c.id === activeConversationId && c.title === 'New Conversation') {
            const short = currentQ.length > 30 ? currentQ.slice(0, 30) + '...' : currentQ;
            return { ...c, title: short };
          }
          return c;
        })
      );
    } catch (err: any) {
      setError(err.message || 'Failed to generate response');
      // Remove optimistic message on error
      setMessages((prev) => prev.filter((m) => m.id !== tempUserMsg.id));
    } finally {
      setSubmitting(false);
    }
  };

  const toggleDocumentSelection = (docId: string) => {
    setSelectedDocIds((prev) =>
      prev.includes(docId) ? prev.filter((id) => id !== docId) : [...prev, docId]
    );
  };

  return (
    <div className="flex h-[calc(100vh-8.5rem)] rounded-2xl border border-slate-800 bg-slate-900/40 overflow-hidden">
      {/* Sidebar - Conversations */}
      <div className="w-64 border-r border-slate-800 bg-slate-950/60 flex flex-col shrink-0">
        <div className="p-3 border-b border-slate-800 flex items-center justify-between">
          <span className="text-xs font-semibold text-slate-300">Conversations</span>
          <button
            onClick={handleCreateConversation}
            className="p-1 rounded-lg bg-emerald-600/10 text-emerald-400 hover:bg-emerald-600/20 border border-emerald-500/20 text-xs flex items-center gap-1 px-2 transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            New
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {conversations.map((conv) => {
            const isActive = conv.id === activeConversationId;
            const isEditing = conv.id === editingConvId;

            return (
              <div
                key={conv.id}
                onClick={() => setActiveConversationId(conv.id)}
                className={`group flex items-center justify-between px-3 py-2 rounded-xl text-xs cursor-pointer transition-colors ${
                  isActive
                    ? 'bg-slate-800 text-white font-medium border border-slate-700'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
                }`}
              >
                {isEditing ? (
                  <div className="flex items-center gap-1.5 flex-1">
                    <input
                      type="text"
                      value={editTitle}
                      onChange={(e) => setEditTitle(e.target.value)}
                      className="w-full bg-slate-950 px-2 py-0.5 rounded text-xs text-white border border-emerald-500 focus:outline-none"
                      autoFocus
                    />
                    <button
                      onClick={(e) => handleSaveRename(conv.id, e)}
                      className="p-0.5 text-emerald-400 hover:text-emerald-300"
                    >
                      <Check className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setEditingConvId(null);
                      }}
                      className="p-0.5 text-slate-400 hover:text-slate-200"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ) : (
                  <>
                    <div className="flex items-center gap-2 truncate">
                      <MessageSquare className="w-3.5 h-3.5 shrink-0 opacity-70" />
                      <span className="truncate">{conv.title}</span>
                    </div>

                    <div className="hidden group-hover:flex items-center gap-1 shrink-0">
                      <button
                        onClick={(e) => handleStartRename(conv, e)}
                        title="Rename"
                        className="p-1 text-slate-400 hover:text-slate-200"
                      >
                        <Edit2 className="w-3 h-3" />
                      </button>
                      <button
                        onClick={(e) => handleDeleteConversation(conv.id, e)}
                        title="Delete"
                        className="p-1 text-slate-400 hover:text-rose-400"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  </>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col bg-slate-900/30 overflow-hidden">
        {/* Document Filter Bar */}
        <div className="px-6 py-3 border-b border-slate-800 bg-slate-900/50 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2">
            <Filter className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            <span className="font-semibold text-slate-300">Search scope:</span>
            <span className="text-slate-400">
              {selectedDocIds.length === 0
                ? 'All Ready Documents'
                : `${selectedDocIds.length} document${selectedDocIds.length > 1 ? 's' : ''} selected`}
            </span>
          </div>

          <div className="flex items-center gap-2">
            {readyDocs.length === 0 ? (
              <span className="text-[11px] text-amber-400">No ready documents indexed yet</span>
            ) : (
              <div className="flex items-center gap-1.5 overflow-x-auto max-w-md py-0.5">
                {readyDocs.map((doc) => {
                  const isSelected = selectedDocIds.includes(doc.id);
                  return (
                    <button
                      key={doc.id}
                      onClick={() => toggleDocumentSelection(doc.id)}
                      className={`px-2 py-0.5 rounded-full text-[11px] font-medium border truncate max-w-[140px] transition-colors ${
                        isSelected
                          ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                          : 'bg-slate-800/80 text-slate-400 border-slate-700 hover:border-slate-600'
                      }`}
                      title={doc.filename}
                    >
                      {doc.filename}
                    </button>
                  );
                })}
                {selectedDocIds.length > 0 && (
                  <button
                    onClick={() => setSelectedDocIds([])}
                    className="text-[10px] text-slate-500 hover:text-slate-300 underline ml-1"
                  >
                    Reset
                  </button>
                )}
              </div>
            )}
          </div>
        </div>

        {error && (
          <div className="m-4 p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Messages Stream */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {loadingConv ? (
            <div className="h-full flex items-center justify-center text-xs text-slate-500">
              Loading conversation...
            </div>
          ) : messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-8">
              <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center justify-center mb-4">
                <Sparkles className="w-6 h-6" />
              </div>
              <h3 className="text-sm font-semibold text-slate-200">Ask DocuQuery anything</h3>
              <p className="text-xs text-slate-400 mt-1 max-w-md">
                Questions are answered strictly using retrieved passages from your uploaded documents, complete with page citations.
              </p>
            </div>
          ) : (
            messages.map((m) => (
              <ChatMessage key={m.id} message={m} onOpenPdf={onOpenPdf} />
            ))
          )}

          {submitting && (
            <div className="flex items-center gap-3 p-4 rounded-xl bg-slate-900/80 border border-slate-800">
              <Loader2 className="w-4 h-4 text-emerald-400 animate-spin" />
              <span className="text-xs text-slate-400">
                Searching passages and generating evidence-grounded answer...
              </span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="p-4 border-t border-slate-800 bg-slate-950/80">
          <form onSubmit={handleSendMessage} className="relative flex items-center">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask a question about your documents..."
              disabled={submitting}
              className="w-full pl-4 pr-12 py-3 bg-slate-900 border border-slate-800 rounded-xl text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-emerald-500 disabled:opacity-50 transition-colors"
            />
            <button
              type="submit"
              disabled={!question.trim() || submitting}
              className="absolute right-2 p-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white transition-colors disabled:opacity-30 disabled:hover:bg-emerald-600"
            >
              <Send className="w-3.5 h-3.5" />
            </button>
          </form>
          <p className="mt-1.5 text-[10px] text-slate-500 text-center">
            DocuQuery never fabricates citations or answers outside provided document evidence.
          </p>
        </div>
      </div>
    </div>
  );
};
