import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bell, Check, Loader2 } from "lucide-react";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Separator } from "../components/ui/separator";
import { ScrollArea } from "../components/ui/scroll-area";
import { notificationsApi, Notification } from "../lib/api";
import { useToast } from "../hooks/use-toast";

const formatTime = (dateString: string): string => {
  const d = new Date(dateString);
  if (isNaN(d.getTime())) return "";
  return d.toLocaleString();
};

export default function Notifications() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();

  const fetchNotifications = async () => {
    setLoading(true);
    const result = await notificationsApi.getNotifications(30);
    if (result.error) {
      toast({
        title: "Error",
        description: result.error,
        variant: "destructive",
      });
      setLoading(false);
      return;
    }
    setNotifications(result.data || []);
    setLoading(false);
  };

  useEffect(() => {
    fetchNotifications();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  const markAllRead = async () => {
    const result = await notificationsApi.markAllAsRead();
    if (result.data) {
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      toast({
        title: "Success",
        description: result.data.message,
      });
    } else if (result.error) {
      toast({
        title: "Error",
        description: result.error,
        variant: "destructive",
      });
    }
  };

  const markOneRead = async (id: number) => {
    const result = await notificationsApi.markAsRead(id);
    if (result.data) {
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)),
      );
    } else if (result.error) {
      toast({
        title: "Error",
        description: result.error,
        variant: "destructive",
      });
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-3xl font-bold tracking-tight">Notifications</h1>
          <p className="text-muted-foreground">
            Your most recent activity updates (last 30).
          </p>
        </div>
        <div className="flex items-center gap-2">
          {unreadCount > 0 && (
            <Badge variant="destructive">{unreadCount} unread</Badge>
          )}
          <Button variant="outline" onClick={markAllRead} disabled={!unreadCount}>
            <Check className="mr-2 h-4 w-4" />
            Mark all read
          </Button>
        </div>
      </div>

      <div className="rounded-xl border bg-card">
        <ScrollArea className="max-h-[70vh]">
          {loading ? (
            <div className="flex items-center justify-center py-10 text-muted-foreground">
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Loading notifications...
            </div>
          ) : notifications.length === 0 ? (
            <div className="py-10 text-center text-muted-foreground">
              <Bell className="mx-auto mb-3 h-6 w-6" />
              No notifications yet.
            </div>
          ) : (
            <div className="divide-y">
              {notifications.map((n) => (
                <div
                  key={n.id}
                  className={`p-4 ${n.is_read ? "" : "bg-accent/40"}`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="space-y-1">
                      <p className="text-sm font-medium">{n.title}</p>
                      <p className="text-sm text-muted-foreground">{n.message}</p>
                      <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                        <span>{formatTime(n.created_at)}</span>
                        <Separator orientation="vertical" className="h-3" />
                        <span className="uppercase tracking-wide">{n.type}</span>
                      </div>
                      {n.related_issue_id && (
                        <Link
                          to={`/issues/${n.related_issue_id}`}
                          className="text-sm text-primary hover:underline"
                        >
                          View issue #{n.related_issue_id}
                        </Link>
                      )}
                    </div>
                    {!n.is_read && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => markOneRead(n.id)}
                      >
                        <Check className="mr-2 h-4 w-4" />
                        Mark read
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </ScrollArea>
      </div>
    </div>
  );
}

