import { useState, useEffect } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  MapPin,
  Calendar,
  User,
  ThumbsUp,
  MessageSquare,
  Send,
} from "lucide-react";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Textarea } from "../components/ui/textarea";
import { Avatar, AvatarImage, AvatarFallback } from "../components/ui/avatar";
import { Separator } from "../components/ui/separator";
import { useToast } from "../hooks/use-toast";
import { issuesApi, IssueDetail } from "../lib/api";

const statusConfig = {
  open: { variant: "info" as const, label: "Open" },
  "in-progress": { variant: "warning" as const, label: "In Progress" },
  resolved: { variant: "success" as const, label: "Resolved" },
  closed: { variant: "secondary" as const, label: "Closed" },
};

const priorityConfig = {
  low: { variant: "secondary" as const, label: "Low Priority" },
  medium: { variant: "info" as const, label: "Medium Priority" },
  high: { variant: "warning" as const, label: "High Priority" },
  critical: { variant: "destructive" as const, label: "Critical" },
};

export default function IssueDetails() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [issue, setIssue] = useState<IssueDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [comment, setComment] = useState("");
  const [postingComment, setPostingComment] = useState(false);
  const [upvoting, setUpvoting] = useState(false);

  useEffect(() => {
    async function fetchIssue() {
      if (!id) return;
      setLoading(true);
      const res = await issuesApi.getIssue(Number(id));
      setIssue(res.data || null);
      setLoading(false);
    }
    fetchIssue();
  }, [id]);

  const status = issue
    ? statusConfig[issue.status as keyof typeof statusConfig]
    : undefined;
  const priority = issue
    ? priorityConfig[issue.priority as keyof typeof priorityConfig]
    : undefined;

  const handleUpvote = async () => {
    if (!issue || upvoting) return;
    setUpvoting(true);
    const res = await issuesApi.upvoteIssue(issue.id);
    if (res.data) {
      setIssue({
        ...issue,
        upvote_count: res.data.upvote_count,
        upvoted_by_user: res.data.upvoted,
      });
    }
    setUpvoting(false);
  };

  const handlePostComment = async () => {
    if (!issue || !comment.trim() || postingComment) return;
    setPostingComment(true);
    const res = await issuesApi.addComment(issue.id, comment);
    if (res.data) {
      setIssue({ ...issue, comments: [...issue.comments, res.data] });
      setComment("");
      toast({
        title: "Comment posted",
        description: "Your comment has been added successfully",
      });
    } else {
      toast({
        title: "Error",
        description: res.error || "Failed to post comment",
        variant: "destructive",
      });
    }
    setPostingComment(false);
  };

  const handleContactSupport = () => {
    toast({
      title: "Contact Support",
      description: "Opening support contact options...",
    });
    window.location.href = `mailto:support@campusfix.edu?subject=Support Request for Issue ${issue?.id}`;
  };

  const currentUserEmail = issue?.reporter?.email || "";
  const isReporter =
    issue && issue.reporter && issue.reporter.email === currentUserEmail;

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto py-12 text-center text-muted-foreground">
        Loading issue details...
      </div>
    );
  }
  if (!issue) {
    return (
      <div className="max-w-4xl mx-auto py-12 text-center text-destructive">
        Issue not found or you do not have access.
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Back Button */}
      <Link
        to="/dashboard"
        className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back to Dashboard
      </Link>

      {/* Edit Issue Button (only for reporter) */}
      {isReporter && (
        <div className="flex justify-end mb-2">
          <Button
            variant="outline"
            onClick={() => navigate(`/issues/${issue.id}/edit`)}
          >
            Edit Issue
          </Button>
        </div>
      )}

      {/* Header */}
      <div className="space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Badge variant={status?.variant}>{status?.label}</Badge>
              <Badge variant={priority?.variant}>{priority?.label}</Badge>
            </div>
            <h1 className="text-3xl font-bold tracking-tight">{issue.title}</h1>
            <p className="text-muted-foreground">#{issue.id}</p>
          </div>

          <Button
            variant={issue.upvoted_by_user ? "default" : "outline"}
            onClick={handleUpvote}
            className="gap-2"
            disabled={upvoting}
          >
            <ThumbsUp
              className={`h-4 w-4 ${issue.upvoted_by_user ? "fill-current" : ""}`}
            />
            <span>{issue.upvote_count}</span>
            Upvote
          </Button>
        </div>

        <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
          <div className="flex items-center gap-1">
            <MapPin className="h-4 w-4" />
            {issue.location}
          </div>
          <div className="flex items-center gap-1">
            <Calendar className="h-4 w-4" />
            {new Date(issue.created_at).toLocaleDateString()}
          </div>
          <div className="flex items-center gap-1">
            <User className="h-4 w-4" />
            Reported by {issue.reporter.first_name} {issue.reporter.last_name}
          </div>
        </div>
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-8">
          {/* Description */}
          <div className="rounded-xl border bg-card p-6">
            <h2 className="text-lg font-semibold mb-4">Description</h2>
            <p className="text-muted-foreground leading-relaxed">
              {issue.description}
            </p>
          </div>

          {/* Timeline */}
          {/* You can implement timeline if your backend supports it, else remove this block */}

          {/* Comments */}
          <div className="rounded-xl border bg-card p-6">
            <h2 className="text-lg font-semibold mb-6 flex items-center gap-2">
              <MessageSquare className="h-5 w-5" />
              Comments ({issue.comments.length})
            </h2>

            {issue.comments.length === 0 ? (
              <div className="text-muted-foreground text-center py-8">
                No comments yet. Be the first to comment!
              </div>
            ) : (
              <div className="space-y-6">
                {issue.comments.map((c) => (
                  <div key={c.id} className="flex gap-4">
                    <Avatar>
                      {c.user.avatar ? (
                        <AvatarImage src={c.user.avatar} alt="Profile" />
                      ) : (
                        <AvatarFallback>
                          {c.user.first_name?.[0] || "?"}
                          {c.user.last_name?.[0] || ""}
                        </AvatarFallback>
                      )}
                    </Avatar>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <p className="font-medium">
                          {c.user.first_name} {c.user.last_name}
                        </p>
                        <Badge variant="secondary" className="text-xs">
                          {c.user.role}
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground mt-1">
                        {c.content}
                      </p>
                      <p className="text-xs text-muted-foreground mt-2">
                        {new Date(c.created_at).toLocaleString()}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}

            <Separator className="my-6" />

            <div className="space-y-4">
              <Textarea
                placeholder="Add a comment..."
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                className="input-focus"
                disabled={postingComment}
              />
              <div className="flex justify-end">
                <Button
                  disabled={!comment.trim() || postingComment}
                  onClick={handlePostComment}
                >
                  <Send className="mr-2 h-4 w-4" />
                  Post Comment
                </Button>
              </div>
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Quick Info */}
          <div className="rounded-xl border bg-card p-6 space-y-4">
            <h3 className="font-semibold">Issue Information</h3>

            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Category</span>
                <span className="font-medium">{issue.category}</span>
              </div>
              <Separator />
              <div className="flex justify-between">
                <span className="text-muted-foreground">Assigned To</span>
                <span className="font-medium text-right text-xs">
                  {issue.assigned_to
                    ? `${issue.assigned_to.first_name} ${issue.assigned_to.last_name}`
                    : "Unassigned"}
                </span>
              </div>
              <Separator />
              <div className="flex justify-between">
                <span className="text-muted-foreground">Upvotes</span>
                <span className="font-medium">{issue.upvote_count}</span>
              </div>
            </div>
          </div>

          {/* Reporter Info */}
          <div className="rounded-xl border bg-card p-6 space-y-4">
            <h3 className="font-semibold">Reporter</h3>
            <div className="flex items-center gap-3">
              <Avatar className="h-12 w-12">
                {issue.reporter.avatar ? (
                  <AvatarImage src={issue.reporter.avatar} alt="Profile" />
                ) : (
                  <AvatarFallback>
                    {issue.reporter.first_name?.[0] || "?"}
                    {issue.reporter.last_name?.[0] || ""}
                  </AvatarFallback>
                )}
              </Avatar>
              <div>
                <p className="font-medium">
                  {issue.reporter.first_name} {issue.reporter.last_name}
                </p>
                <p className="text-sm text-muted-foreground">
                  {issue.reporter.student_id}
                </p>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="rounded-xl border bg-muted/50 p-6 space-y-3">
            <h3 className="font-semibold">Need Help?</h3>
            <p className="text-sm text-muted-foreground">
              If this is urgent, contact facilities directly.
            </p>
            <Button
              variant="outline"
              className="w-full"
              onClick={handleContactSupport}
            >
              Contact Support
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
