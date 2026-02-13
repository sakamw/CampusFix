import { useState, useCallback } from "react";
import { Search, User, Menu } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useToast } from "@/hooks/use-toast";
import { NotificationDropdown } from "./NotificationDropdown";
import { useAuth } from "@/contexts/AuthContext";
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";
import { useUserSettings } from "@/contexts/UserSettingsContext";

interface HeaderProps {
  onMenuClick?: () => void;
}

export function Header({ onMenuClick }: HeaderProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const { toast } = useToast();
  const { logout } = useAuth();
  const [searchQuery, setSearchQuery] = useState("");

  const { settings } = useUserSettings();

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    // Navigate to issues page with search query
    navigate(`/issues?search=${encodeURIComponent(searchQuery)}`);
    setSearchQuery("");
  };

  const handleProfile = () => {
    navigate("/settings");
  };

  const handleSettings = () => {
    const settingsPath = location.pathname.startsWith("/admin")
      ? "/admin/settings"
      : "/settings";
    navigate(settingsPath);
  };

  const handleSignOut = async () => {
    await logout();
    toast({
      title: "Signed out",
      description: "You have been successfully signed out",
    });
    navigate("/login");
  };

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-card shadow-sm">
      <div className="flex h-16 items-center gap-4 px-4 md:px-6">
        <Button
          variant="ghost"
          size="icon"
          className="md:hidden"
          onClick={onMenuClick}
        >
          <Menu className="h-5 w-5" />
        </Button>

        <Link to="/dashboard" className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
            <span className="text-sm font-bold text-primary-foreground">
              CF
            </span>
          </div>
          <span className="hidden font-semibold text-foreground md:inline-block">
            CampusFix
          </span>
        </Link>

        <div className="ml-auto flex items-center gap-4">
          <form onSubmit={handleSearch} className="relative hidden md:block">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search issues..."
              className="w-64 pl-9 input-focus"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </form>

          <NotificationDropdown />

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="rounded-full">
                <Avatar className="h-8 w-8">
                  {settings.profile.avatar ? (
                    <AvatarImage src={settings.profile.avatar} alt="Profile" />
                  ) : (
                    <AvatarFallback>
                      {settings.profile.firstName[0]}
                      {settings.profile.lastName[0]}
                    </AvatarFallback>
                  )}
                </Avatar>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel>My Account</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={handleProfile}>
                Profile
              </DropdownMenuItem>
              <DropdownMenuItem onClick={handleSettings}>
                Settings
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={handleSignOut}>
                Sign out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  );
}
