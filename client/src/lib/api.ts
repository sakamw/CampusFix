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
      return { error: data.error || data.detail || 'An error occurred' };
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

export { getAccessToken, getRefreshToken, clearTokens, setTokens };
export type { UserData, LoginResponse, RegisterResponse, ApiResponse };
