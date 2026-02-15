import {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from "react";
import { authApi, getAccessToken, clearTokens, UserData } from "../lib/api";

interface AuthContextType {
  user: UserData | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (
    email: string,
    password: string,
  ) => Promise<{ success: boolean; error?: string; user?: UserData }>;
  register: (userData: {
    email: string;
    first_name: string;
    last_name: string;
    student_id: string;
    password: string;
    password_confirm: string;
  }) => Promise<{ success: boolean; error?: string }>;
  logout: () => Promise<void>;
  updateUser: (data: Partial<UserData>) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserData | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Check for existing session on mount
  useEffect(() => {
    const checkAuth = async () => {
      const token = getAccessToken();
      if (token) {
        const result = await authApi.getProfile();
        if (result.data) {
          setUser(result.data);
        } else {
          clearTokens();
        }
      }
      setIsLoading(false);
    };

    checkAuth();
  }, []);

  const login = async (email: string, password: string) => {
    const result = await authApi.login(email, password);

    if (result.data) {
      setUser(result.data.user);
      return { success: true, user: result.data.user };
    }

    return { success: false, error: result.error };
  };

  const register = async (userData: {
    email: string;
    first_name: string;
    last_name: string;
    student_id: string;
    password: string;
    password_confirm: string;
  }) => {
    const result = await authApi.register(userData);

    if (result.data) {
      setUser(result.data.user);
      return { success: true };
    }

    return { success: false, error: result.error };
  };

  const logout = async () => {
    await authApi.logout();
    setUser(null);
  };

  const updateUser = (data: Partial<UserData>) => {
    if (user) {
      setUser({ ...user, ...data });
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        register,
        logout,
        updateUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
