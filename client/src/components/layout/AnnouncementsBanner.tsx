import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { announcementsApi, Announcement } from "../../lib/api";
import { Button } from "../ui/button";
import { useToast } from "../../hooks/use-toast";

export function AnnouncementsBanner() {
  const { toast } = useToast();
  const [announcements, setAnnouncements] = useState<Announcement[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      const res = await announcementsApi.getAnnouncements();
      if (res.data) {
        setAnnouncements(res.data);
      }
      setLoading(false);
    };
    load();
  }, []);

  const handleDismiss = async (id: number) => {
    const prev = announcements;
    setAnnouncements((items) => items.filter((a) => a.id !== id));
    const res = await announcementsApi.dismissAnnouncement(id);
    if (res.error) {
      // Revert on error
      setAnnouncements(prev);
      toast({
        title: "Could not dismiss",
        description: res.error,
        variant: "destructive",
      });
    }
  };

  if (loading || announcements.length === 0) {
    return null;
  }

  return (
    <div className="mb-4 space-y-3">
      {announcements.map((a) => (
        <div
          key={a.id}
          className="flex flex-col gap-2 rounded-lg border bg-accent/10 px-4 py-3 text-sm md:flex-row md:items-start md:gap-3"
        >
          <div className="flex-1">
            <p className="font-semibold">{a.title}</p>
            <p className="text-xs text-muted-foreground whitespace-pre-line">
              {a.body}
            </p>
          </div>
          <div className="flex items-center justify-end gap-2 md:justify-start">
            {a.expires_at && (
              <span className="text-[0.7rem] text-muted-foreground">
                Until {new Date(a.expires_at).toLocaleDateString()}
              </span>
            )}
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={() => handleDismiss(a.id)}
            >
              <X className="h-3 w-3" />
            </Button>
          </div>
        </div>
      ))}
    </div>
  );
}

