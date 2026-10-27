import {
  User,
  TokenResponse,
  DocumentItem,
  DocumentListResponse,
  Conversation,
  ConversationDetail,
  ChatResponse,
  SystemStats,
} from '../types';

const API_BASE = '/api/v1';

class ApiClient {
  private getAccessToken(): string | null {
    return localStorage.getItem('dq_access_token');
  }

  private getRefreshToken(): string | null {
    return localStorage.getItem('dq_refresh_token');
  }

  public setTokens(tokens: TokenResponse) {
    localStorage.setItem('dq_access_token', tokens.access_token);
    localStorage.setItem('dq_refresh_token', tokens.refresh_token);
  }

  public clearTokens() {
    localStorage.removeItem('dq_access_token');
    localStorage.removeItem('dq_refresh_token');
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const token = this.getAccessToken();
    const headers = new Headers(options.headers || {});

    if (token && !headers.has('Authorization')) {
      headers.set('Authorization', `Bearer ${token}`);
    }

    if (!(options.body instanceof FormData) && !headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json');
    }

    let response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    });

    // Handle token refresh on 401
    if (response.status === 401 && this.getRefreshToken() && !endpoint.includes('/auth/')) {
      const refreshed = await this.tryRefreshToken();
      if (refreshed) {
        const retryHeaders = new Headers(options.headers || {});
        retryHeaders.set('Authorization', `Bearer ${this.getAccessToken()}`);
        if (!(options.body instanceof FormData) && !retryHeaders.has('Content-Type')) {
          retryHeaders.set('Content-Type', 'application/json');
        }
        response = await fetch(`${API_BASE}${endpoint}`, {
          ...options,
          headers: retryHeaders,
        });
      } else {
        this.clearTokens();
        window.dispatchEvent(new Event('auth_logout'));
        throw new Error('Session expired. Please log in again.');
      }
    }

    if (!response.ok) {
      let errorMsg = `Request failed (${response.status})`;
      try {
        const errorData = await response.json();
        errorMsg = errorData.detail || errorMsg;
      } catch {
        // Fallback to status text
      }
      throw new Error(errorMsg);
    }

    if (response.status === 204) {
      return {} as T;
    }

    return response.json();
  }

  private async tryRefreshToken(): Promise<boolean> {
    const refresh = this.getRefreshToken();
    if (!refresh) return false;
    try {
      const resp = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refresh }),
      });
      if (resp.ok) {
        const data: TokenResponse = await resp.json();
        this.setTokens(data);
        return true;
      }
    } catch {
      // Failed to refresh
    }
    return false;
  }

  // Auth Endpoints
  public async login(email: string, password: string): Promise<TokenResponse> {
    const data = await this.request<TokenResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    this.setTokens(data);
    return data;
  }

  public async register(email: string, password: string, fullName?: string): Promise<User> {
    return this.request<User>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, full_name: fullName }),
    });
  }

  public async getMe(): Promise<User> {
    return this.request<User>('/auth/me');
  }

  // Document Endpoints
  public async listDocuments(search?: string, limit = 50, offset = 0): Promise<DocumentListResponse> {
    const params = new URLSearchParams();
    if (search) params.set('search', search);
    params.set('limit', limit.toString());
    params.set('offset', offset.toString());
    return this.request<DocumentListResponse>(`/documents?${params.toString()}`);
  }

  public async uploadDocument(file: File): Promise<DocumentItem> {
    const formData = new FormData();
    formData.append('file', file);
    return this.request<DocumentItem>('/documents/upload', {
      method: 'POST',
      body: formData,
    });
  }

  public async getDocument(id: string): Promise<DocumentItem> {
    return this.request<DocumentItem>(`/documents/${id}`);
  }

  public async getDocumentStatus(id: string): Promise<{ id: string; status: string; page_count: number; error_message?: string }> {
    return this.request(`/documents/${id}/status`);
  }

  public async retryDocument(id: string): Promise<DocumentItem> {
    return this.request<DocumentItem>(`/documents/${id}/retry`, {
      method: 'POST',
    });
  }

  public async deleteDocument(id: string): Promise<void> {
    return this.request<void>(`/documents/${id}`, {
      method: 'DELETE',
    });
  }

  public getDocumentPdfUrl(id: string): string {
    const token = this.getAccessToken();
    return token
      ? `${API_BASE}/documents/${id}/download?token=${encodeURIComponent(token)}`
      : `${API_BASE}/documents/${id}/download`;
  }

  // Conversation Endpoints
  public async listConversations(): Promise<Conversation[]> {
    return this.request<Conversation[]>('/conversations');
  }

  public async createConversation(title?: string): Promise<Conversation> {
    return this.request<Conversation>('/conversations', {
      method: 'POST',
      body: JSON.stringify({ title }),
    });
  }

  public async getConversation(id: string): Promise<ConversationDetail> {
    return this.request<ConversationDetail>(`/conversations/${id}`);
  }

  public async renameConversation(id: string, title: string): Promise<Conversation> {
    return this.request<Conversation>(`/conversations/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ title }),
    });
  }

  public async deleteConversation(id: string): Promise<void> {
    return this.request<void>(`/conversations/${id}`, {
      method: 'DELETE',
    });
  }

  // Chat Endpoint
  public async sendMessage(
    conversationId: string,
    question: string,
    selectedDocumentIds?: string[]
  ): Promise<ChatResponse> {
    return this.request<ChatResponse>(`/chat/conversations/${conversationId}/messages`, {
      method: 'POST',
      body: JSON.stringify({
        question,
        selected_document_ids: selectedDocumentIds && selectedDocumentIds.length > 0 ? selectedDocumentIds : null,
      }),
    });
  }

  // System Stats
  public async getStats(): Promise<SystemStats> {
    return this.request<SystemStats>('/system/stats');
  }
}

export const api = new ApiClient();
