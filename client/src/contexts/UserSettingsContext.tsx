import {
  createContext,
  useContext,
  useState,
  ReactNode,
  useEffect,
} from "react";
import { authApi } from "../lib/api";
import { uploadImageToCloudinary, updateUserAvatarUrl } from "../lib/cloudinary";

interface UserProfile {
  firstName: string;
  lastName: string;
  email: string;
  studentId: string;
  phone: string;
  avatar: string | null;
}

interface SecuritySettings {
  twoFactorEnabled: boolean;
}

type Theme = "light" | "dark" | "system";

interface AppearanceSettings {
  theme: Theme;
}

interface UserSettings {
  profile: UserProfile;
  security: SecuritySettings;
  appearance: AppearanceSettings;
}

interface UserSettingsContextType {
  settings: UserSettings;
  updateProfile: (profile: Partial<UserProfile>) => Promise<void>;
  updateAvatar: (avatar: string | null | File) => Promise<void>;
  updateSecurity: (settings: Partial<SecuritySettings>) => Promise<void>;
  updateAppearance: (settings: Partial<AppearanceSettings>) => void;
  resetSettings: () => void;
}

const defaultSettings: UserSettings = {
  profile: {
    firstName: "",
    lastName: "",
    email: "",
    studentId: "",
    phone: "",
    avatar: null,
  },
  security: {
    twoFactorEnabled: false,
  },
  appearance: {
    theme: "system" as Theme,
  },
};

const STORAGE_KEY = "campusfix-user-settings";

const UserSettingsContext = createContext<UserSettingsContextType | undefined>(
  undefined,
);

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

  // Fetch user profile from server and update settings
  const fetchUserProfile = async () => {
    try {
      const res = await authApi.getProfile();
      if (res.data) {
        setSettings((prev) => ({
          ...prev,
          profile: {
            ...prev.profile,
            firstName: res.data.first_name || prev.profile.firstName,
            lastName: res.data.last_name || prev.profile.lastName,
            email: res.data.email || prev.profile.email,
            studentId: res.data.student_id || prev.profile.studentId,
            phone: res.data.phone || "", // Ensure empty string instead of null
            avatar: res.data.avatar || prev.profile.avatar,
          },
          security: {
            ...prev.security,
            twoFactorEnabled: res.data.two_factor_enabled || false,
          },
        }));
      }
    } catch (e) {
      // Optionally handle error
    }
  };

  // Fetch on mount and when window regains focus
  useEffect(() => {
    fetchUserProfile();
    const onFocus = () => fetchUserProfile();
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, []);

  // Persist settings to localStorage whenever they change
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
  }, [settings]);

  const updateProfile = async (profile: Partial<UserProfile>) => {
    // Update local state immediately for responsive UI
    setSettings((prev) => ({
      ...prev,
      profile: { ...prev.profile, ...profile },
    }));
    
    // Sync with server
    try {
      await authApi.updateProfile({
        first_name: profile.firstName,
        last_name: profile.lastName,
        phone: profile.phone,
      });
      
      // Refresh user profile to ensure sync
      await fetchUserProfile();
    } catch (error) {
      console.error('Failed to update profile:', error);
      // Revert to previous state on error
      await fetchUserProfile();
      throw error;
    }
  };

  const updateAvatar = async (avatar: string | null | File) => {
    try {
      let avatarUrl: string | null = null;
      
      if (avatar instanceof File) {
        // Upload file to Cloudinary via backend
        avatarUrl = await uploadImageToCloudinary(avatar);
      } else if (typeof avatar === 'string') {
        avatarUrl = avatar;
      }
      
      // Update local state immediately for responsive UI
      setSettings((prev) => ({
        ...prev,
        profile: { ...prev.profile, avatar: avatarUrl },
      }));
      
      // If it's a file upload, the backend already updated the avatar
      // If it's a URL update or removal, sync with server
      if (avatar instanceof File) {
        // Backend already updated the avatar, just refresh to ensure sync
        await fetchUserProfile();
      } else {
        // Handle URL update or removal
        if (avatarUrl) {
          await updateUserAvatarUrl(avatarUrl);
        } else {
          // Handle avatar removal - update profile with null avatar
          await authApi.updateProfile({ avatar: null });
        }
        await fetchUserProfile();
      }
    } catch (error) {
      console.error('Failed to update avatar:', error);
      // Revert to previous state on error
      await fetchUserProfile();
      throw error;
    }
  };

  const updateSecurity = async (securitySettings: Partial<SecuritySettings>) => {
    // Update local state immediately for responsive UI
    setSettings((prev) => ({
      ...prev,
      security: { ...prev.security, ...securitySettings },
    }));
    
    // Sync with server if two_factor_enabled is being updated
    if ('twoFactorEnabled' in securitySettings) {
      try {
        await authApi.updateTwoFactor(securitySettings.twoFactorEnabled!);
        // Refresh user profile to ensure sync
        await fetchUserProfile();
      } catch (error) {
        console.error('Failed to update two-factor setting:', error);
        // Revert to previous state on error
        await fetchUserProfile();
        throw error;
      }
    }
  };

  const updateAppearance = (
    appearanceSettings: Partial<AppearanceSettings>,
  ) => {
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
        updateSecurity,
        updateAppearance,
        resetSettings,
      }}
    >
      {children}
    </UserSettingsContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useUserSettings() {
  const context = useContext(UserSettingsContext);
  if (context === undefined) {
    throw new Error(
      "useUserSettings must be used within a UserSettingsProvider",
    );
  }
  return context;
}

export type { Theme };
