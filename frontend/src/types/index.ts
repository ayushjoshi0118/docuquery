export interface User {
  id: string;
  email: string;
  full_name?: string | null;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export type DocumentStatus = 'queued' | 'processing' | 'ready' | 'failed';

export interface DocumentItem {
  id: string;
  filename: string;
  file_size: number;
  page_count: number;
  checksum: string;
  status: DocumentStatus;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentListResponse {
  items: DocumentItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface Citation {
  document_id: string;
  filename: string;
  page_number: number;
  excerpt: string;
  chunk_id: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  citations?: Citation[] | null;
  created_at: string;
}

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface ConversationDetail {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages: Message[];
}

export interface ChatResponse {
  user_message: Message;
  assistant_message: Message;
}

export interface SystemStats {
  total_documents: number;
  ready_documents: number;
  failed_documents: number;
  total_pages: number;
  storage_used_bytes: number;
  total_conversations: number;
  total_queries: number;
}
