import {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
} from "react";
import { useLocation } from "react-router-dom";
import { useAuth } from "./AuthContext";
import { useUserSettings, Theme } from "./UserSettingsContext";

// Public routes that should always use light theme
const PUBLIC_ROUTES = ["/login", "/forgot-password", "/"];

interface ThemeContextType {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  resolvedTheme: "light" | "dark";
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const location = useLocation();
  const { isAuthenticated } = useAuth();
  const { settings, updateAppearance } = useUserSettings();
  const [resolvedTheme, setResolvedTheme] = useState<"light" | "dark">("light");

  // Check if current route is a public route
  const isPublicRoute = PUBLIC_ROUTES.includes(location.pathname);

  // Get theme from user settings only if authenticated AND not on a public route
  const theme: Theme =
    isAuthenticated && !isPublicRoute ? settings.appearance.theme : "light";

  useEffect(() => {
    const root = window.document.documentElement;

    const applyTheme = (newTheme: Theme) => {
      let effectiveTheme: "light" | "dark";

      // Always use light theme on public routes
      if (isPublicRoute) {
        effectiveTheme = "light";
      } else if (newTheme === "system") {
        effectiveTheme = window.matchMedia("(prefers-color-scheme: dark)")
          .matches
          ? "dark"
          : "light";
      } else {
        effectiveTheme = newTheme;
      }

      root.classList.remove("light", "dark");
      root.classList.add(effectiveTheme);
      setResolvedTheme(effectiveTheme);
    };

    applyTheme(theme);

    // Listen for system theme changes (only when not on public route and using system theme)
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    const handleChange = () => {
      if (!isPublicRoute && theme === "system") {
        applyTheme("system");
      }
    };

    mediaQuery.addEventListener("change", handleChange);
    return () => mediaQuery.removeEventListener("change", handleChange);
  }, [theme, isPublicRoute]);

  const setTheme = (newTheme: Theme) => {
    // Only save theme if user is authenticated
    if (isAuthenticated) {
      updateAppearance({ theme: newTheme });
    }
  };

  return (
    <ThemeContext.Provider value={{ theme, setTheme, resolvedTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error("useTheme must be used within a ThemeProvider");
  }
  return context;
}

export type { Theme };
