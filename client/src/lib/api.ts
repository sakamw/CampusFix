const API_BASE_URL = 'http://localhost:8000/api';

interface ApiResponse<T = unknown> {
  data?: T;
  error?: string;
}

interface TokenResponse {
  access: string;
  refresh: string;
}

interface UserData {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  student_id: string | null;
  phone: string | null;
  role: 'student' | 'admin';
  avatar: string | null;
  created_at: string;
  is_superuser: boolean;
  is_staff: boolean;
}

interface LoginResponse {
  user: UserData;
  tokens: TokenResponse;
  message: string;
}

interface RegisterResponse {
  user: UserData;
  tokens: TokenResponse;
  message: string;
}

// Token management
const getAccessToken = (): string | null => {
  return localStorage.getItem('access_token');
};

const getRefreshToken = (): string | null => {
  return localStorage.getItem('refresh_token');
};

const setTokens = (access: string, refresh: string): void => {
  localStorage.setItem('access_token', access);
  localStorage.setItem('refresh_token', refresh);
};

const clearTokens = (): void => {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
};

// Refresh token
const refreshAccessToken = async (): Promise<string | null> => {
  const refresh = getRefreshToken();
  if (!refresh) return null;

  try {
    const response = await fetch(`${API_BASE_URL}/auth/token/refresh/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refresh }),
    });

    if (response.ok) {
      const data = await response.json();
      localStorage.setItem('access_token', data.access);
      return data.access;
    }
  } catch {
    // Refresh failed
  }

  clearTokens();
  return null;
};

// Parse API errors into user-friendly messages
const parseApiError = (data: unknown): string => {
  if (!data || typeof data !== 'object') return 'Something went wrong. Please try again.';
  
  const err = data as Record<string, unknown>;
  
  // Direct error/detail message
  if (typeof err.error === 'string') return friendlyMessage(err.error);
  if (typeof err.detail === 'string') return friendlyMessage(err.detail);
  
  // Field validation errors
  for (const [, errors] of Object.entries(err)) {
    if (Array.isArray(errors) && errors.length > 0) {
      return friendlyMessage(String(errors[0]));
    }
  }
  
  return 'Something went wrong. Please try again.';
};

const friendlyMessage = (msg: string): string => {
  const m = msg.toLowerCase();
  if (m.includes('too short') || m.includes('at least 8')) return 'Password must be at least 8 characters.';
  if (m.includes('too common')) return 'Password is too common. Choose a stronger one.';
  if (m.includes('entirely numeric')) return 'Password cannot be all numbers.';
  if (m.includes('too similar')) return 'Password is too similar to your personal info.';
  if (m.includes('already exists')) return 'An account with this email already exists.';
  if (m.includes('do not match')) return 'Passwords do not match.';
  if (m.includes('invalid') || m.includes('incorrect')) return 'Invalid email or password.';
  if (m.includes('required') || m.includes('blank')) return 'Please fill in all required fields.';
  return msg;
};

// API fetch wrapper
const apiFetch = async <T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> => {
  const url = `${API_BASE_URL}${endpoint}`;
  
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  const token = getAccessToken();
  if (token) {
    (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
  }

  try {
    let response = await fetch(url, { ...options, headers });

    // If unauthorized, try to refresh token
    if (response.status === 401 && token) {
      const newToken = await refreshAccessToken();
      if (newToken) {
        (headers as Record<string, string>)['Authorization'] = `Bearer ${newToken}`;
        response = await fetch(url, { ...options, headers });
      }
    }

    const data = await response.json();

    if (!response.ok) {
      return { error: parseApiError(data) };
    }

    return { data };
  } catch (error) {
    return { error: 'Network error. Please try again.' };
  }
};

// Auth API
export const authApi = {
  login: async (email: string, password: string): Promise<ApiResponse<LoginResponse>> => {
    const result = await apiFetch<LoginResponse>('/auth/login/', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });

    if (result.data) {
      setTokens(result.data.tokens.access, result.data.tokens.refresh);
    }

    return result;
  },

  register: async (userData: {
    email: string;
    first_name: string;
    last_name: string;
    student_id: string;
    password: string;
    password_confirm: string;
  }): Promise<ApiResponse<RegisterResponse>> => {
    const result = await apiFetch<RegisterResponse>('/auth/register/', {
      method: 'POST',
      body: JSON.stringify(userData),
    });

    if (result.data) {
      setTokens(result.data.tokens.access, result.data.tokens.refresh);
    }

    return result;
  },

  logout: async (): Promise<void> => {
    const refresh = getRefreshToken();
    if (refresh) {
      await apiFetch('/auth/logout/', {
        method: 'POST',
        body: JSON.stringify({ refresh }),
      });
    }
    clearTokens();
  },

  getProfile: async (): Promise<ApiResponse<UserData>> => {
    return apiFetch<UserData>('/auth/profile/');
  },

  updateProfile: async (data: Partial<UserData>): Promise<ApiResponse<UserData>> => {
    return apiFetch<UserData>('/auth/profile/', {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  changePassword: async (
    oldPassword: string,
    newPassword: string,
    newPasswordConfirm: string
  ): Promise<ApiResponse<{ message: string }>> => {
    return apiFetch('/auth/change-password/', {
      method: 'POST',
      body: JSON.stringify({
        old_password: oldPassword,
        new_password: newPassword,
        new_password_confirm: newPasswordConfirm,
      }),
    });
  },

  forgotPassword: async (email: string): Promise<ApiResponse<{ message: string; reset_token?: string }>> => {
    return apiFetch('/auth/forgot-password/', {
      method: 'POST',
      body: JSON.stringify({ email }),
    });
  },

  resetPassword: async (
    token: string,
    newPassword: string,
    newPasswordConfirm: string
  ): Promise<ApiResponse<{ message: string }>> => {
    return apiFetch('/auth/reset-password/', {
      method: 'POST',
      body: JSON.stringify({
        token,
        new_password: newPassword,
        new_password_confirm: newPasswordConfirm,
      }),
    });
  },
};

// Issue types
export interface Issue {
  id: number;
  title: string;
  description: string;
  category: string;
  status: 'open' | 'in-progress' | 'resolved' | 'closed';
  priority: 'low' | 'medium' | 'high' | 'critical';
  location: string;
  reporter: UserData;
  assigned_to: UserData | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
  upvote_count: number;
  upvoted_by_user: boolean;
}

export interface IssueDetail extends Issue {
  comments: Comment[];
  attachments: Attachment[];
  comment_count: number;
}

export interface Comment {
  id: number;
  issue: number;
  user: UserData;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface Attachment {
  id: number;
  issue: number;
  file: string;
  filename: string;
  uploaded_by: UserData;
  uploaded_at: string;
}

export interface Notification {
  id: number;
  user: number;
  title: string;
  message: string;
  type: 'comment' | 'status_change' | 'assignment' | 'upvote' | 'resolution' | 'system';
  is_read: boolean;
  related_issue: number | null;
  related_issue_id: number | null;
  related_issue_title: string | null;
  created_at: string;
}

export interface DashboardStats {
  total_issues: number;
  open_issues: number;
  in_progress_issues: number;
  resolved_issues: number;
  closed_issues: number;
  resolution_rate: number;
  avg_response_time_hours: number;
}

// Issues API
export const issuesApi = {
  getIssues: async (params?: {
    status?: string;
    priority?: string;
    category?: string;
    search?: string;
    filter?: 'my-issues' | 'assigned-to-me';
  }): Promise<ApiResponse<Issue[]>> => {
    const queryParams = new URLSearchParams();
    if (params?.status) queryParams.append('status', params.status);
    if (params?.priority) queryParams.append('priority', params.priority);
    if (params?.category) queryParams.append('category', params.category);
    if (params?.search) queryParams.append('search', params.search);
    if (params?.filter) queryParams.append('filter', params.filter);
    
    const query = queryParams.toString();
    return apiFetch<Issue[]>(`/issues/${query ? `?${query}` : ''}`);
  },

  getIssue: async (id: number): Promise<ApiResponse<IssueDetail>> => {
    return apiFetch<IssueDetail>(`/issues/${id}/`);
  },

  createIssue: async (data: {
    title: string;
    description: string;
    category: string;
    priority: string;
    location: string;
  }): Promise<ApiResponse<Issue>> => {
    return apiFetch<Issue>('/issues/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  updateIssue: async (id: number, data: Partial<Issue>): Promise<ApiResponse<Issue>> => {
    return apiFetch<Issue>(`/issues/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  deleteIssue: async (id: number): Promise<ApiResponse<void>> => {
    return apiFetch<void>(`/issues/${id}/`, {
      method: 'DELETE',
    });
  },

  upvoteIssue: async (id: number): Promise<ApiResponse<{ message: string; upvoted: boolean; upvote_count: number }>> => {
    return apiFetch(`/issues/${id}/upvote/`, {
      method: 'POST',
    });
  },

  getComments: async (issueId: number): Promise<ApiResponse<Comment[]>> => {
    return apiFetch<Comment[]>(`/issues/${issueId}/comments/`);
  },

  addComment: async (issueId: number, content: string): Promise<ApiResponse<Comment>> => {
    return apiFetch<Comment>(`/issues/${issueId}/comments/`, {
      method: 'POST',
      body: JSON.stringify({ content }),
    });
  },
};

// Notifications API
export const notificationsApi = {
  getNotifications: async (): Promise<ApiResponse<Notification[]>> => {
    return apiFetch<Notification[]>('/notifications/');
  },

  markAsRead: async (id: number): Promise<ApiResponse<Notification>> => {
    return apiFetch<Notification>(`/notifications/${id}/mark_read/`, {
      method: 'POST',
    });
  },

  markAllAsRead: async (): Promise<ApiResponse<{ message: string; count: number }>> => {
    return apiFetch(`/notifications/mark_all_read/`, {
      method: 'POST',
    });
  },

  getUnreadCount: async (): Promise<ApiResponse<{ unread_count: number }>> => {
    return apiFetch('/notifications/unread_count/');
  },
};

// Dashboard API
export const dashboardApi = {
  getStats: async (): Promise<ApiResponse<DashboardStats>> => {
    return apiFetch<DashboardStats>('/dashboard/stats/');
  },

  getRecentIssues: async (limit: number = 5): Promise<ApiResponse<Issue[]>> => {
    return apiFetch<Issue[]>(`/dashboard/recent_issues/?limit=${limit}`);
  },

  getAdminStats: async (): Promise<ApiResponse<DashboardStats & {
    category_stats: { category: string; count: number }[];
    priority_stats: { priority: string; count: number }[];
  }>> => {
    return apiFetch('/dashboard/admin_stats/');
  },
};

export { getAccessToken, getRefreshToken, clearTokens, setTokens };
export type { UserData, LoginResponse, RegisterResponse, ApiResponse };
