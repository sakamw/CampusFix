import { useEffect, useState } from "react";
import { Trophy, AlertCircle, Loader2 } from "lucide-react";
import { dashboardApi, LeaderboardEntry } from "../lib/api";
import { useToast } from "../hooks/use-toast";
import { Button } from "../components/ui/button";

type LeaderboardMode = "this_month" | "all_time";

export default function Leaderboard() {
  const { toast } = useToast();
  const [mode, setMode] = useState<LeaderboardMode>("this_month");
  const [thisMonth, setThisMonth] = useState<LeaderboardEntry[]>([]);
  const [allTime, setAllTime] = useState<LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await dashboardApi.getLeaderboard();
        if (res.error) {
          throw new Error(res.error);
        }
        setThisMonth(res.data?.this_month || []);
        setAllTime(res.data?.all_time || []);
      } catch (err) {
        const msg =
          err instanceof Error ? err.message : "Failed to load leaderboard.";
        setError(msg);
        toast({
          title: "Error",
          description: msg,
          variant: "destructive",
        });
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [toast]);

  const entries = mode === "this_month" ? thisMonth : allTime;

  const renderName = (entry: LeaderboardEntry) => {
    if (entry.reporter__first_name || entry.reporter__last_name) {
      return `${entry.reporter__first_name || ""} ${
        entry.reporter__last_name || ""
      }`.trim();
    }
    return entry.reporter__email;
  };

  if (loading && !thisMonth.length && !allTime.length) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (error && !thisMonth.length && !allTime.length) {
    return (
      <div className="flex h-[50vh] flex-col items-center justify-center gap-4">
        <AlertCircle className="h-12 w-12 text-destructive" />
        <p className="text-lg text-muted-foreground">{error}</p>
        <Button onClick={() => window.location.reload()}>Retry</Button>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
            <Trophy className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">
              Reporter Leaderboard
            </h1>
            <p className="text-muted-foreground">
              See the most active student reporters on CampusFix.
            </p>
          </div>
        </div>
      </div>

      <div className="flex flex-wrap gap-3">
        <Button
          type="button"
          variant={mode === "this_month" ? "default" : "outline"}
          size="sm"
          onClick={() => setMode("this_month")}
        >
          This Month
        </Button>
        <Button
          type="button"
          variant={mode === "all_time" ? "default" : "outline"}
          size="sm"
          onClick={() => setMode("all_time")}
        >
          All Time
        </Button>
      </div>

      <div className="rounded-xl border bg-card p-4 md:p-6">
        {entries.length === 0 ? (
          <div className="py-8 text-center text-muted-foreground">
            No reports yet for this period.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-xs uppercase tracking-wide text-muted-foreground">
                  <th className="py-2 pr-4">Rank</th>
                  <th className="py-2 pr-4">Reporter</th>
                  <th className="py-2 pr-4">Email</th>
                  <th className="py-2 pr-4 text-right">Issues Reported</th>
                  <th className="py-2 pr-4 text-right">Issues Resolved</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((entry, index) => (
                  <tr
                    key={`${mode}-${entry.reporter_id}-${index}`}
                    className="border-b last:border-0"
                  >
                    <td className="py-2 pr-4">
                      <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-muted text-xs font-semibold">
                        {index + 1}
                      </span>
                    </td>
                    <td className="py-2 pr-4 font-medium">
                      {renderName(entry)}
                    </td>
                    <td className="py-2 pr-4 text-muted-foreground">
                      {entry.reporter__email}
                    </td>
                    <td className="py-2 pr-4 text-right">
                      {entry.total_issues}
                    </td>
                    <td className="py-2 pr-4 text-right">
                      {entry.issues_resolved}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
