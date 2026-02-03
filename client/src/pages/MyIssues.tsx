import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { PlusCircle, Loader2, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { IssueTable } from "@/components/dashboard/IssueTable";
import { issuesApi, Issue } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";

export default function MyIssues() {
  const [issues, setIssues] = useState<Issue[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { toast } = useToast();

  useEffect(() => {
    fetchMyIssues();

    // Auto-refresh every 30 seconds
    const interval = setInterval(() => {
      fetchMyIssues(true);
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  const fetchMyIssues = async (silent = false) => {
    if (!silent) setLoading(true);
    setError(null);

    try {
      const result = await issuesApi.getIssues({ filter: 'my-issues' });
      
      if (result.error) {
        throw new Error(result.error);
      }

      setIssues(result.data || []);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load issues';
      setError(errorMessage);
      if (!silent) {
        toast({
          title: 'Error',
          description: errorMessage,
          variant: 'destructive',
        });
      }
    } finally {
      setLoading(false);
    }
  };

  if (loading && issues.length === 0) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (error && issues.length === 0) {
    return (
      <div className="flex h-[50vh] flex-col items-center justify-center gap-4">
        <AlertCircle className="h-12 w-12 text-destructive" />
        <p className="text-lg text-muted-foreground">{error}</p>
        <Button onClick={() => fetchMyIssues()}>Retry</Button>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">My Issues</h1>
          <p className="text-muted-foreground">
            View and manage all the issues you've reported.
          </p>
        </div>
        <Button asChild size="lg">
          <Link to="/report">
            <PlusCircle className="mr-2 h-5 w-5" />
            Report New Issue
          </Link>
        </Button>
      </div>

      {/* Issues Table */}
      {issues.length > 0 ? (
        <IssueTable issues={issues} />
      ) : (
        <div className="rounded-xl border bg-card p-12 text-center">
          <p className="text-lg font-medium text-muted-foreground mb-2">
            No issues reported yet
          </p>
          <p className="text-sm text-muted-foreground mb-6">
            Start by reporting your first issue to get help with campus facilities.
          </p>
          <Button asChild>
            <Link to="/report">
              <PlusCircle className="mr-2 h-4 w-4" />
              Report Your First Issue
            </Link>
          </Button>
        </div>
      )}
    </div>
  );
}

