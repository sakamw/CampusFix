import { NavLink, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  PlusCircle,
  FileText,
  Settings,
  BarChart3,
  Users,
  X,
} from "lucide-react";
import { cn } from "../../lib/utils";
import { Button } from "../../components/ui/button";
import { useToast } from "../../hooks/use-toast";

interface SidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
}

const studentNavItems = [
  { title: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { title: "Report Issue", href: "/report", icon: PlusCircle },
  { title: "My Issues", href: "/issues", icon: FileText },
  { title: "Public Posts", href: "/public-issues", icon: FileText },
  { title: "Settings", href: "/settings", icon: Settings },
];

const adminNavItems = [
  { title: "Dashboard", href: "/admin", icon: LayoutDashboard },
  { title: "All Issues", href: "/admin/issues", icon: FileText },
  { title: "Analytics", href: "/admin/analytics", icon: BarChart3 },
  { title: "Users", href: "/admin/users", icon: Users },
  { title: "Settings", href: "/admin/settings", icon: Settings },
];

export function Sidebar({ isOpen, onClose }: SidebarProps) {
  const location = useLocation();
  const { toast } = useToast();
  const isAdmin = location.pathname.startsWith("/admin");
  const navItems = isAdmin ? adminNavItems : studentNavItems;

  const handleGetSupport = () => {
    toast({
      title: "Get Support",
      description: "Opening support options...",
    });
    window.location.href =
      "mailto:support@campusfix.edu?subject=Support Request";
  };

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-foreground/20 backdrop-blur-sm md:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          // Fixed on mobile, sticky on desktop
          "fixed left-0 top-0 z-50 h-full w-64 transform border-r bg-card transition-transform duration-200 md:sticky md:top-0 md:self-start md:translate-x-0",
          isOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex h-16 items-center justify-between border-b px-4 md:hidden">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
              <span className="text-sm font-bold text-primary-foreground">
                CF
              </span>
            </div>
            <span className="font-semibold">CampusFix</span>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-5 w-5" />
          </Button>
        </div>

        <div className="flex flex-col h-[calc(100%-4rem)] md:h-full">
          <nav className="flex flex-col gap-1 p-4 pt-6 md:pt-4 flex-1">
            <p className="mb-2 px-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">
              {isAdmin ? "Administration" : "Navigation"}
            </p>
            {navItems.map((item) => (
              <NavLink
                key={item.href}
                to={item.href}
                onClick={onClose}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground",
                  )
                }
              >
                <item.icon className="h-5 w-5" />
                {item.title}
              </NavLink>
            ))}
          </nav>

          {!isAdmin && (
            <div className="p-4 mt-auto">
              <div className="rounded-lg border bg-muted/50 p-4">
                <p className="text-sm font-medium">Need help?</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Contact IT support for urgent issues
                </p>
                <Button
                  size="sm"
                  variant="secondary"
                  className="mt-3 w-full"
                  onClick={handleGetSupport}
                >
                  Get Support
                </Button>
              </div>
            </div>
          )}
        </div>
      </aside>
    </>
  );
}
