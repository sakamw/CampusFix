import { useState, useEffect } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  FileText,
  AlertCircle,
  CheckCircle2,
  Clock,
  PlusCircle,
  TrendingUp,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { StatCard } from "@/components/dashboard/StatCard";
import { IssueTable } from "@/components/dashboard/IssueTable";
import { dashboardApi, Issue, DashboardStats } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";

export default function Dashboard() {
  const [searchParams] = useSearchParams();
  const { toast } = useToast();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [issues, setIssues] = useState<Issue[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const searchQuery = searchParams.get("search");

  useEffect(() => {
    fetchDashboardData();

    // Auto-refresh every 30 seconds
    const interval = setInterval(() => {
      fetchDashboardData(true);
    }, 30000);

    return () => clearInterval(interval);
  }, [searchQuery]);

  const fetchDashboardData = async (silent = false) => {
    if (!silent) setLoading(true);
    setError(null);

    try {
      // Fetch stats and recent issues in parallel
      const [statsResult, issuesResult] = await Promise.all([
        dashboardApi.getStats(),
        dashboardApi.getRecentIssues(5),
      ]);

      if (statsResult.error) {
        throw new Error(statsResult.error);
      }
      if (issuesResult.error) {
        throw new Error(issuesResult.error);
      }

      // Set data or defaults for new users
      setStats(
        statsResult.data || {
          total_issues: 0,
          open_issues: 0,
          in_progress_issues: 0,
          resolved_issues: 0,
          closed_issues: 0,
          resolution_rate: 0,
          avg_response_time_hours: 0,
        },
      );
      setIssues(issuesResult.data || []);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to load dashboard data";
      setError(errorMessage);
      if (!silent) {
        toast({
          title: "Error",
          description: errorMessage,
          variant: "destructive",
        });
      }
    } finally {
      setLoading(false);
    }
  };

  if (loading && !stats) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (error && !stats) {
    return (
      <div className="flex h-[50vh] flex-col items-center justify-center gap-4">
        <AlertCircle className="h-12 w-12 text-destructive" />
        <p className="text-lg text-muted-foreground">{error}</p>
        <Button onClick={() => fetchDashboardData()}>Retry</Button>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">
            {searchQuery
              ? `Search results for "${searchQuery}"`
              : "Welcome back! Here's an overview of your reported issues."}
          </p>
        </div>
        <Button asChild size="lg">
          <Link to="/report">
            <PlusCircle className="mr-2 h-5 w-5" />
            Report New Issue
          </Link>
        </Button>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Issues"
          value={stats?.total_issues || 0}
          description="All time reported"
          icon={FileText}
          variant="primary"
        />
        <StatCard
          title="Open Issues"
          value={stats?.open_issues || 0}
          description="Awaiting resolution"
          icon={AlertCircle}
        />
        <StatCard
          title="In Progress"
          value={stats?.in_progress_issues || 0}
          description="Currently being addressed"
          icon={Clock}
          variant="warning"
        />
        <StatCard
          title="Resolved"
          value={stats?.resolved_issues || 0}
          description="Successfully completed"
          icon={CheckCircle2}
          variant="success"
        />
      </div>

      {/* Quick Stats Banner */}
      <div className="rounded-xl border bg-gradient-to-r from-primary/5 via-accent/5 to-primary/5 p-6">
        <div className="flex items-center gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
            <TrendingUp className="h-6 w-6 text-primary" />
          </div>
          <div>
            <p className="font-medium">Your Resolution Rate</p>
            <p className="text-2xl font-bold text-primary">
              {stats?.resolution_rate || 0}%
            </p>
          </div>
          <div className="ml-auto text-right">
            <p className="text-sm text-muted-foreground">
              Average Response Time
            </p>
            <p className="text-lg font-semibold">
              {stats?.avg_response_time_hours || 0} hours
            </p>
          </div>
        </div>
      </div>

      {/* Recent Issues */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold">Recent Issues</h2>
          <Button variant="ghost" asChild>
            <Link to="/issues">View all issues</Link>
          </Button>
        </div>
        {issues.length > 0 ? (
          <IssueTable issues={issues} />
        ) : (
          <div className="rounded-lg border bg-card p-8 text-center">
            <p className="text-muted-foreground">
              No issues reported yet. Click "Report New Issue" to get started.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
