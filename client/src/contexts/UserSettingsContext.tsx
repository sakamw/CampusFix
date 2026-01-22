import { createContext, useContext, useState, ReactNode, useEffect } from "react";

interface UserProfile {
  firstName: string;
  lastName: string;
  email: string;
  studentId: string;
  phone: string;
  avatar: string | null;
}

interface NotificationPreferences {
  emailNotifications: boolean;
  pushNotifications: boolean;
  issueUpdates: boolean;
  issueComments: boolean;
  weeklyDigest: boolean;
  marketingEmails: boolean;
}

interface SecuritySettings {
  twoFactorEnabled: boolean;
}

type Theme = "light" | "dark" | "system";

interface AppearanceSettings {
  language: string;
  theme: Theme;
}

interface UserSettings {
  profile: UserProfile;
  notifications: NotificationPreferences;
  security: SecuritySettings;
  appearance: AppearanceSettings;
}

interface UserSettingsContextType {
  settings: UserSettings;
  updateProfile: (profile: Partial<UserProfile>) => void;
  updateAvatar: (avatar: string | null) => void;
  updateNotifications: (prefs: Partial<NotificationPreferences>) => void;
  updateSecurity: (settings: Partial<SecuritySettings>) => void;
  updateAppearance: (settings: Partial<AppearanceSettings>) => void;
  resetSettings: () => void;
}

const defaultSettings: UserSettings = {
  profile: {
    firstName: "John",
    lastName: "Doe",
    email: "john.doe@university.edu",
    studentId: "STU123456",
    phone: "+1 (555) 123-4567",
    avatar: null,
  },
  notifications: {
    emailNotifications: true,
    pushNotifications: true,
    issueUpdates: true,
    issueComments: true,
    weeklyDigest: false,
    marketingEmails: false,
  },
  security: {
    twoFactorEnabled: false,
  },
  appearance: {
    language: "en",
    theme: "light" as Theme,
  },
};

const STORAGE_KEY = "campusfix-user-settings";

const UserSettingsContext = createContext<UserSettingsContextType | undefined>(undefined);

export function UserSettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<UserSettings>(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        try {
          return { ...defaultSettings, ...JSON.parse(stored) };
        } catch {
          return defaultSettings;
        }
      }
    }
    return defaultSettings;
  });

  // Persist settings to localStorage whenever they change
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
  }, [settings]);

  const updateProfile = (profile: Partial<UserProfile>) => {
    setSettings((prev) => ({
      ...prev,
      profile: { ...prev.profile, ...profile },
    }));
  };

  const updateAvatar = (avatar: string | null) => {
    setSettings((prev) => ({
      ...prev,
      profile: { ...prev.profile, avatar },
    }));
  };

  const updateNotifications = (prefs: Partial<NotificationPreferences>) => {
    setSettings((prev) => ({
      ...prev,
      notifications: { ...prev.notifications, ...prefs },
    }));
  };

  const updateSecurity = (securitySettings: Partial<SecuritySettings>) => {
    setSettings((prev) => ({
      ...prev,
      security: { ...prev.security, ...securitySettings },
    }));
  };

  const updateAppearance = (appearanceSettings: Partial<AppearanceSettings>) => {
    setSettings((prev) => ({
      ...prev,
      appearance: { ...prev.appearance, ...appearanceSettings },
    }));
  };

  const resetSettings = () => {
    setSettings(defaultSettings);
    localStorage.removeItem(STORAGE_KEY);
  };

  return (
    <UserSettingsContext.Provider
      value={{
        settings,
        updateProfile,
        updateAvatar,
        updateNotifications,
        updateSecurity,
        updateAppearance,
        resetSettings,
      }}
    >
      {children}
    </UserSettingsContext.Provider>
  );
}

export function useUserSettings() {
  const context = useContext(UserSettingsContext);
  if (context === undefined) {
    throw new Error("useUserSettings must be used within a UserSettingsProvider");
  }
  return context;
}

export type { Theme };
