import { Location } from "react-router-dom";

interface UserData {
  is_superuser?: boolean;
  role?: string;
}

/**
 * Get the appropriate redirect path after authentication
 * @param location - React Router location object containing state
 * @param userData - User data to determine role-based redirects
 * @returns The path to redirect to (including search params if any)
 */
export function getAuthRedirectPath(location: Location, userData?: UserData): string {
  // Check if there's a saved destination from the protected route
  const from = location.state?.from as { pathname: string; search: string };
  if (from) {
    // Include both pathname and search parameters
    return from.pathname + (from.search || '');
  }
  
  // Default redirect based on user role
  if (userData?.is_superuser || userData?.role === "admin") {
    return "/admin";
  } else {
    return "/dashboard";
  }
}

/**
 * Get redirect path for registration (doesn't have user data yet)
 * @param location - React Router location object containing state
 * @returns The path to redirect to (including search params if any)
 */
export function getRegisterRedirectPath(location: Location): string {
  // Check if there's a saved destination from the protected route
  const from = location.state?.from as { pathname: string; search: string };
  if (from) {
    // Include both pathname and search parameters
    return from.pathname + (from.search || '');
  }
  
  // Default to dashboard for new users
  return "/dashboard";
}
