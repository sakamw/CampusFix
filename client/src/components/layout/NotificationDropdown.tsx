import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  Bell,
  Check,
  MessageSquare,
  AlertCircle,
  UserPlus,
  CheckCircle,
  Info,
} from "lucide-react";
import { Button } from "../../components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "../../components/ui/dropdown-menu";
import { ScrollArea } from "../../components/ui/scroll-area";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "../../components/ui/dialog";
import { notificationsApi, Notification } from "../../lib/api";
import { useToast } from "../../hooks/use-toast";
import { cn } from "../../lib/utils";

const notificationIcons = {
  comment: MessageSquare,
  status_change: AlertCircle,
  assignment: UserPlus,
  upvote: CheckCircle,
  resolution: CheckCircle,
  system: Info,
};

const formatTimeAgo = (dateString: string): string => {
  const date = new Date(dateString);
  const now = new Date();
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;
  return date.toLocaleDateString();
};

export function NotificationDropdown() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [selectedNotification, setSelectedNotification] = useState<Notification | null>(null);
  const { toast } = useToast();

  useEffect(() => {
    fetchNotifications();
    fetchUnreadCount();

    // Poll for new notifications every 30 seconds
    const interval = setInterval(() => {
      fetchUnreadCount();
      if (isOpen) {
        fetchNotifications();
      }
    }, 30000);

    return () => clearInterval(interval);
  }, [isOpen]);

  const fetchNotifications = async () => {
    setLoading(true);
    const result = await notificationsApi.getNotifications(10);
    if (result.data) {
      setNotifications(result.data);
    }
    setLoading(false);
  };

  const fetchUnreadCount = async () => {
    const result = await notificationsApi.getUnreadCount();
    if (result.data) {
      setUnreadCount(result.data.unread_count);
    }
  };

  const handleMarkAsRead = async (id: number, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();

    const result = await notificationsApi.markAsRead(id);
    if (result.data) {
      setNotifications(
        notifications.map((n) => (n.id === id ? { ...n, is_read: true } : n)),
      );
      setUnreadCount(Math.max(0, unreadCount - 1));
    }
  };

  const handleMarkAllAsRead = async () => {
    const result = await notificationsApi.markAllAsRead();
    if (result.data) {
      setNotifications(notifications.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
      toast({
        title: "Success",
        description: result.data.message,
      });
    }
  };

  const handleOpenChange = (open: boolean) => {
    setIsOpen(open);
    if (open) {
      fetchNotifications();
    }
  };

  const handleNotificationClick = (e: React.MouseEvent, notification: Notification) => {
    if (!notification.related_issue_id) {
      e.preventDefault();
      setIsOpen(false); // Close dropdown
      setSelectedNotification(notification);
      
      // Mark as read automatically when viewing full details
      if (!notification.is_read) {
        handleMarkAsRead(notification.id, e);
      }
    }
  };

  return (
    <>
    <DropdownMenu onOpenChange={handleOpenChange} open={isOpen}>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="relative">
          <Bell className="h-5 w-5" />
          {unreadCount > 0 && (
            <span className="absolute right-1 top-1 flex h-4 w-4 items-center justify-center rounded-full bg-destructive text-[10px] font-bold text-destructive-foreground">
              {unreadCount > 9 ? "9+" : unreadCount}
            </span>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80">
        <div className="flex items-center justify-between px-2 py-2">
          <DropdownMenuLabel className="p-0">Notifications</DropdownMenuLabel>
          {unreadCount > 0 && (
            <Button
              variant="ghost"
              size="sm"
              className="h-auto p-1 text-xs"
              onClick={handleMarkAllAsRead}
            >
              Mark all read
            </Button>
          )}
        </div>
        <DropdownMenuSeparator />
        <ScrollArea className="max-h-[400px]">
          {loading && notifications.length === 0 ? (
            <div className="p-4 text-center text-sm text-muted-foreground">
              Loading notifications...
            </div>
          ) : notifications.length === 0 ? (
            <div className="p-4 text-center text-sm text-muted-foreground">
              No notifications yet
            </div>
          ) : (
            notifications.map((notification) => {
              const Icon = notificationIcons[notification.type];
              return (
                <DropdownMenuItem
                  key={notification.id}
                  className={cn(
                    "flex cursor-pointer flex-col items-start gap-1 p-3",
                    !notification.is_read && "bg-accent/50",
                  )}
                  asChild
                >
                  <Link
                    to={
                      notification.related_issue_id
                        ? `/issues/${notification.related_issue_id}`
                        : "#"
                    }
                    onClick={(e) => handleNotificationClick(e, notification)}
                    className="w-full"
                  >
                    <div className="flex w-full items-start gap-2">
                      <Icon className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                      <div className="flex-1 space-y-1">
                        <p className="text-sm font-medium leading-none">
                          {notification.title}
                        </p>
                        <p className="text-xs text-muted-foreground line-clamp-2">
                          {notification.message}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {formatTimeAgo(notification.created_at)}
                        </p>
                      </div>
                      {!notification.is_read && (
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-6 w-6 shrink-0"
                          onClick={(e) => handleMarkAsRead(notification.id, e)}
                        >
                          <Check className="h-3 w-3" />
                        </Button>
                      )}
                    </div>
                  </Link>
                </DropdownMenuItem>
              );
            })
          )}
        </ScrollArea>
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link
            to="/notifications"
            className="w-full text-sm text-muted-foreground"
          >
            View all notifications
          </Link>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>

    <Dialog open={!!selectedNotification} onOpenChange={(open) => !open && setSelectedNotification(null)}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {selectedNotification && (() => {
              const Icon = notificationIcons[selectedNotification.type] || Info;
              return <Icon className="h-5 w-5 text-primary" />;
            })()}
            {selectedNotification?.title}
          </DialogTitle>
          <DialogDescription>
            {selectedNotification && formatTimeAgo(selectedNotification.created_at)}
          </DialogDescription>
        </DialogHeader>
        <div className="py-4">
          <p className="text-sm whitespace-pre-wrap leading-relaxed text-foreground">
            {selectedNotification?.message}
          </p>
        </div>
        <div className="flex justify-end">
          <Button onClick={() => setSelectedNotification(null)}>Close</Button>
        </div>
      </DialogContent>
    </Dialog>
    </>
  );
}
