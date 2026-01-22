import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { Loader2 } from "lucide-react";

interface ProtectedRouteProps {
  children: React.ReactNode;
  requireAdmin?: boolean;
}

export function ProtectedRoute({ children, requireAdmin = false }: ProtectedRouteProps) {
  const { user, isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!isAuthenticated) {
    // Redirect to login, but save the attempted URL
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (requireAdmin && !user?.is_superuser && user?.role !== 'admin') {
    // Non-admin trying to access admin routes - redirect to regular dashboard
    return <Navigate to="/dashboard" replace />;
  }

  // Admin users trying to access regular routes - redirect to admin dashboard
  if (!requireAdmin && (user?.is_superuser || user?.role === 'admin')) {
    return <Navigate to="/admin" replace />;
  }

  return <>{children}</>;
}
