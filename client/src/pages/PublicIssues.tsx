import { useState, useEffect } from "react";
import { Loader2, AlertCircle, Globe2 } from "lucide-react";
import { IssueTable } from "../components/dashboard/IssueTable";
import { issuesApi, Issue } from "../lib/api";
import { useToast } from "../hooks/use-toast";

export default function PublicIssues() {
  const [issues, setIssues] = useState<Issue[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { toast } = useToast();

  useEffect(() => {
    fetchPublicIssues();
    const interval = setInterval(() => fetchPublicIssues(true), 30000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchPublicIssues = async (silent = false) => {
    if (!silent) setLoading(true);
    setError(null);
    try {
      const result = await issuesApi.getIssues({});
      if (result.error) throw new Error(result.error);
      setIssues(
        (result.data || []).filter((issue) => issue.visibility === "public"),
      );
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to load public issues";
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
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Public Posts</h1>
          <p className="text-muted-foreground">
            Browse and view all issues marked as public by users.
          </p>
        </div>
      </div>

      {/* Issues Table */}
      {issues.length > 0 ? (
        <IssueTable issues={issues} />
      ) : (
        <div className="rounded-xl border bg-card p-12 text-center">
          <p className="text-lg font-medium text-muted-foreground mb-2">
            No public issues yet
          </p>
          <p className="text-sm text-muted-foreground mb-6">
            When users report public issues, they will appear here for everyone
            to see.
          </p>
        </div>
      )}
    </div>
  );
}
