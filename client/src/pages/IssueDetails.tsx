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
  CheckCircle2,
  Paperclip,
  Download,
  Wrench,
} from "lucide-react";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Input } from "../components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import { Textarea } from "../components/ui/textarea";
import { Avatar, AvatarImage, AvatarFallback } from "../components/ui/avatar";
import { Separator } from "../components/ui/separator";
import { useToast } from "../hooks/use-toast";
import { useAuth } from "../contexts/AuthContext";
import { issuesApi, IssueDetail, TimelineEvent } from "../lib/api";
import Timeline from "../components/Timeline";

const statusConfig = {
  open: { variant: "secondary" as const, label: "Pending" },
  "in-progress": { variant: "info" as const, label: "In Progress" },
  awaiting_verification: {
    variant: "warning" as const,
    label: "Awaiting Verification",
  },
  resolved: { variant: "success" as const, label: "Resolved" },
  reopened: { variant: "destructive" as const, label: "Reopened" },
  closed: { variant: "secondary" as const, label: "Closed" },
};

const priorityConfig = {
  low: { variant: "secondary" as const, label: "Low Priority" },
  medium: { variant: "info" as const, label: "Medium Priority" },
  high: { variant: "warning" as const, label: "High Priority" },
  critical: { variant: "destructive" as const, label: "Critical" },
};

// Helper function to format file size
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
};

export default function IssueDetails() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const { user } = useAuth();
  const [issue, setIssue] = useState<IssueDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [comment, setComment] = useState("");
  const [postingComment, setPostingComment] = useState(false);
  const [upvoting, setUpvoting] = useState(false);
  const [timelineEvents, setTimelineEvents] = useState<TimelineEvent[]>([]);
  const [timelineLoading, setTimelineLoading] = useState(true);
  const [etaNow, setEtaNow] = useState<Date>(() => new Date());
  const [adminSaving, setAdminSaving] = useState(false);
  const [adminFields, setAdminFields] = useState<{
    status: IssueDetail["status"];
    estimated_resolution_text: string;
    estimated_completion_date: string; // YYYY-MM-DD
  } | null>(null);
  const [feedbackRating, setFeedbackRating] = useState<number | null>(null);
  const [feedbackComment, setFeedbackComment] = useState("");
  const [submittingFeedback, setSubmittingFeedback] = useState(false);

  const isAdmin = user?.is_superuser || user?.role === "admin";

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

  useEffect(() => {
    const t = setInterval(() => setEtaNow(new Date()), 60_000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    if (!issue) return;
    const dateOnly = issue.estimated_completion
      ? new Date(issue.estimated_completion).toISOString().slice(0, 10)
      : "";
    setAdminFields({
      status: issue.status,
      estimated_resolution_text: issue.estimated_resolution_text || "",
      estimated_completion_date: dateOnly,
    });

    // Initialize feedback state from server, if present
    if (issue.my_feedback) {
      setFeedbackRating(issue.my_feedback.rating);
      setFeedbackComment(issue.my_feedback.comment || "");
    } else {
      setFeedbackRating(null);
      setFeedbackComment("");
    }
  }, [issue]);

  useEffect(() => {
    async function fetchTimeline() {
      if (!id) return;
      setTimelineLoading(true);
      const res = await issuesApi.getTimeline(Number(id));
      setTimelineEvents(res.data || []);
      setTimelineLoading(false);
    }
    fetchTimeline();
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
        description: "Failed to post comment",
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
  const isReporter = !!(
    currentUserEmail &&
    user?.email &&
    currentUserEmail === user.email
  );
  const canComment = isReporter || isAdmin;

  const roleBadge = (role: string | undefined) => {
    const r = (role || "").toLowerCase();
    if (r === "admin") return { label: "Admin", variant: "default" as const };
    if (r === "staff") return { label: "Staff", variant: "info" as const };
    return { label: "Student", variant: "secondary" as const };
  };

  const handleSubmitFeedback = async () => {
    if (!issue || !isReporter || submittingFeedback || !feedbackRating) return;
    setSubmittingFeedback(true);
    try {
      const res = await issuesApi.submitFeedback(issue.id, {
        rating: feedbackRating,
        comment: feedbackComment.trim() || undefined,
      });
      if (res.error) {
        throw new Error(res.error);
      }
      toast({
        title: "Thank you!",
        description: "Your feedback has been recorded.",
      });
      // Optimistically update local issue state
      setIssue((prev) =>
        prev
          ? {
              ...prev,
              my_feedback: {
                rating: feedbackRating,
                comment: feedbackComment,
                created_at: new Date().toISOString(),
              },
              feedback_count: (prev.feedback_count || 0) + (prev.my_feedback ? 0 : 1),
            }
          : prev,
      );
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to submit feedback.";
      toast({
        title: "Error",
        description: msg,
        variant: "destructive",
      });
    } finally {
      setSubmittingFeedback(false);
    }
  };

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

  const formatEstimatedResolution = () => {
    if (
      issue.estimated_resolution_text &&
      issue.estimated_resolution_text.trim()
    ) {
      return issue.estimated_resolution_text.trim();
    }
    if (issue.estimated_completion) {
      const d = new Date(issue.estimated_completion);
      if (!isNaN(d.getTime())) {
        return d.toLocaleDateString();
      }
    }
    return "Not set";
  };

  const getCountdown = () => {
    if (!issue.estimated_completion) return null;
    const due = new Date(issue.estimated_completion);
    if (isNaN(due.getTime())) return null;
    const diffMs = due.getTime() - etaNow.getTime();
    const abs = Math.abs(diffMs);
    const days = Math.floor(abs / (1000 * 60 * 60 * 24));
    const hours = Math.floor((abs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    if (diffMs >= 0) return `Due in ${days}d ${hours}h`;
    return `Overdue by ${days}d ${hours}h`;
  };

  const saveAdminUpdates = async () => {
    if (!issue || !adminFields || adminSaving) return;
    setAdminSaving(true);
    try {
      const estimated_completion = adminFields.estimated_completion_date?.trim()
        ? `${adminFields.estimated_completion_date.trim()}T00:00:00Z`
        : null;

      const res = await issuesApi.updateIssue(issue.id, {
        status: adminFields.status,
        estimated_resolution_text: adminFields.estimated_resolution_text,
        estimated_completion,
      });

      if (res.error) throw new Error(res.error);
      if (res.data) {
        toast({
          title: "Saved",
          description: "Issue updates have been saved.",
        });
        // refresh view with latest
        setIssue((prev) => (prev ? { ...prev, ...res.data } : prev));
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to save";
      toast({
        title: "Error",
        description: msg,
        variant: "destructive",
      });
    } finally {
      setAdminSaving(false);
    }
  };

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
            {issue.is_anonymous ? (
              "Reported by Anonymous User"
            ) : (
              <>
                Reported by {issue.reporter.first_name}{" "}
                {issue.reporter.last_name}
              </>
            )}
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

          {/* Reporter Attachments */}
          {issue.attachments && issue.attachments.length > 0 && (
            <div className="rounded-xl border bg-card p-6 space-y-4">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <Paperclip className="h-5 w-5 text-primary" />
                Attachments ({issue.attachments.length})
              </h2>
              <p className="text-xs text-muted-foreground">
                Images and files uploaded when this issue was reported.
              </p>
              <div className="grid gap-4 grid-cols-2 md:grid-cols-4">
                {issue.attachments.map((attachment) => {
                  const url = attachment.file;
                  const lower = url.toLowerCase();
                  const isImage = /\.(jpg|jpeg|png|gif)$/.test(lower);
                  const isVideo = /\.(mp4|webm|mov|avi|mkv)$/.test(lower);

                  return (
                    <div
                      key={attachment.id}
                      className="group relative rounded-lg border bg-muted/40 overflow-hidden"
                    >
                      {isImage && (
                        <a href={url} target="_blank" rel="noopener noreferrer">
                          <img
                            src={url}
                            alt={attachment.filename}
                            className="h-32 w-full object-cover"
                          />
                        </a>
                      )}
                      {isVideo && (
                        <video
                          controls
                          className="h-32 w-full object-cover bg-black"
                        >
                          <source src={url} />
                        </video>
                      )}
                      {!isImage && !isVideo && (
                        <div className="p-3 text-xs">
                          <a
                            href={url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center gap-2 text-primary hover:underline"
                          >
                            <Download className="h-3 w-3" />
                            <span className="truncate">
                              {attachment.filename}
                            </span>
                          </a>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Timeline */}
          {timelineLoading ? (
            <div className="rounded-xl border bg-card p-6">
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <Calendar className="h-5 w-5" />
                Timeline
              </h2>
              <div className="text-muted-foreground text-center py-8">
                Loading timeline...
              </div>
            </div>
          ) : (
            <Timeline events={timelineEvents} />
          )}

          {/* Staff Progress Log (read-only) */}
          {issue.progress_logs && issue.progress_logs.length > 0 && (
            <div className="rounded-xl border bg-card p-6 space-y-4">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <Wrench className="h-5 w-5" />
                Work Log (Staff)
              </h2>
              <div className="space-y-4">
                {issue.progress_logs.map((log) => (
                  <div
                    key={log.id}
                    className="rounded-lg border-2 border-gray-300 bg-gray-50 p-4 space-y-3"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge variant="secondary">{log.log_type}</Badge>
                        <span className="text-sm font-bold text-gray-900">
                          {log.staff.first_name} {log.staff.last_name}
                        </span>
                      </div>
                      <span className="text-xs text-gray-600">
                        {new Date(log.created_at).toLocaleString()}
                      </span>
                    </div>
                    <p className="text-base font-medium text-black whitespace-pre-wrap">
                      {log.description}
                    </p>
                    {log.photo && (
                      <a
                        href={log.photo}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-block"
                      >
                        <img
                          src={log.photo}
                          alt="Progress"
                          className="h-28 w-40 rounded-md object-cover border"
                        />
                      </a>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

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
                        <Badge
                          variant={roleBadge(c.user.role).variant}
                          className="text-xs"
                        >
                          {roleBadge(c.user.role).label}
                        </Badge>
                        <span className="text-xs text-muted-foreground">
                          {new Date(c.created_at).toLocaleString()}
                        </span>
                      </div>
                      <p className="text-sm text-muted-foreground mt-1">
                        {c.content}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}

            <Separator className="my-6" />

            <div className="space-y-4">
              {canComment ? (
                <>
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
                </>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Only the original reporter and campus staff can comment on
                  this issue.
                </p>
              )}
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
                <span className="text-muted-foreground">Upvotes</span>
                <span className="font-medium">{issue.upvote_count}</span>
              </div>
              <Separator />
              <div className="space-y-1">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">
                    Estimated Resolution
                  </span>
                  <span className="font-medium text-right">
                    {formatEstimatedResolution() === "Not set"
                      ? "Not set"
                      : `Estimated: ${formatEstimatedResolution()}`}
                  </span>
                </div>
                {issue.estimated_completion && (
                  <p className="text-xs text-muted-foreground">
                    {getCountdown()}
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Admin/Staff Controls */}
          {isAdmin && adminFields && (
            <div className="rounded-xl border bg-card p-6 space-y-4">
              <h3 className="font-semibold">Admin Controls</h3>
              <div className="space-y-3">
                <div className="space-y-2">
                  <span className="text-sm text-muted-foreground">Status</span>
                  <Select
                    value={adminFields.status}
                    onValueChange={(v) =>
                      setAdminFields((prev) =>
                        prev
                          ? { ...prev, status: v as IssueDetail["status"] }
                          : prev,
                      )
                    }
                  >
                    <SelectTrigger className="input-focus">
                      <SelectValue placeholder="Select status" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="open">Pending</SelectItem>
                      <SelectItem value="in-progress">In Progress</SelectItem>
                      <SelectItem value="awaiting_verification">
                        Awaiting Verification
                      </SelectItem>
                      <SelectItem value="resolved">Resolved</SelectItem>
                      <SelectItem value="reopened">Reopened</SelectItem>
                      <SelectItem value="closed">Closed</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <span className="text-sm text-muted-foreground">
                    Estimated Resolution (text)
                  </span>
                  <Input
                    placeholder='e.g. "2–3 business days"'
                    value={adminFields.estimated_resolution_text}
                    onChange={(e) =>
                      setAdminFields((prev) =>
                        prev
                          ? {
                              ...prev,
                              estimated_resolution_text: e.target.value,
                            }
                          : prev,
                      )
                    }
                    className="input-focus"
                  />
                </div>

                <div className="space-y-2">
                  <span className="text-sm text-muted-foreground">
                    Estimated Completion (date)
                  </span>
                  <Input
                    type="date"
                    value={adminFields.estimated_completion_date}
                    onChange={(e) =>
                      setAdminFields((prev) =>
                        prev
                          ? {
                              ...prev,
                              estimated_completion_date: e.target.value,
                            }
                          : prev,
                      )
                    }
                    className="input-focus"
                  />
                  <p className="text-xs text-muted-foreground">
                    If set, a countdown will appear for all viewers.
                  </p>
                </div>

                <Button onClick={saveAdminUpdates} disabled={adminSaving}>
                  {adminSaving ? "Saving..." : "Save Updates"}
                </Button>
              </div>
            </div>
          )}

          {/* Resolution Information - Show if resolved */}
          {(issue.status === "resolved" || issue.status === "closed") && (
            <div className="rounded-xl border bg-card p-6 space-y-4">
              <h3 className="font-semibold flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5 text-green-600" />
                Resolution Report
              </h3>

              {issue.resolution_summary && (
                <div className="space-y-2">
                  <p className="text-sm font-medium text-muted-foreground">
                    Summary:
                  </p>
                  <p className="text-sm">{issue.resolution_summary}</p>
                </div>
              )}

              {issue.resolution_details && (
                <div className="space-y-2">
                  <p className="text-sm font-medium text-muted-foreground">
                    Details:
                  </p>
                  <p className="text-sm whitespace-pre-wrap">
                    {issue.resolution_details}
                  </p>
                </div>
              )}

              {issue.resolution_evidence && (
                <div className="space-y-2">
                  <p className="text-sm font-medium text-muted-foreground">
                    Evidence:
                  </p>
                  <p className="text-sm whitespace-pre-wrap">
                    {issue.resolution_evidence}
                  </p>
                </div>
              )}

              {issue.actual_completion && (
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Completed:</span>
                  <span className="font-medium">
                    {new Date(issue.actual_completion).toLocaleDateString()}
                  </span>
                </div>
              )}

              {issue.work_hours && (
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Work Hours:</span>
                  <span className="font-medium">{issue.work_hours} hours</span>
                </div>
              )}

              {issue.evidence_files && issue.evidence_files.length > 0 && (
                <div className="space-y-3">
                  <p className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                    <Paperclip className="h-4 w-4" />
                    Evidence Files ({issue.evidence_files.length})
                  </p>
                  <div className="space-y-2">
                    {issue.evidence_files.map((evidence) => (
                      <div
                        key={evidence.id}
                        className="flex items-center justify-between p-2 rounded border bg-muted/50"
                      >
                        <div className="flex-1">
                          <a
                            href={evidence.file}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sm font-medium hover:text-primary hover:underline flex items-center gap-2"
                          >
                            <Download className="h-3 w-3" />
                            {evidence.filename}
                          </a>
                          <p className="text-xs text-muted-foreground">
                            {evidence.file_type} •{" "}
                            {formatFileSize(evidence.file_size)} • Uploaded by{" "}
                            {evidence.admin
                              ? `${evidence.admin.first_name} ${evidence.admin.last_name}`
                              : "Unknown"}
                          </p>
                          {evidence.description && (
                            <p className="text-xs text-muted-foreground mt-1">
                              {evidence.description}
                            </p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Rate This Resolution */}
          {isReporter &&
            (issue.status === "resolved" || issue.status === "closed") && (
              <div className="rounded-xl border bg-card p-6 space-y-4">
                <h3 className="font-semibold">How was your experience?</h3>
                <p className="text-sm text-muted-foreground">
                  Rate the resolution so campus staff can keep improving.
                </p>
                <div className="flex flex-wrap items-center gap-2">
                  {[1, 2, 3, 4, 5].map((n) => (
                    <Button
                      key={n}
                      type="button"
                      variant={feedbackRating === n ? "default" : "outline"}
                      size="sm"
                      onClick={() => setFeedbackRating(n)}
                      disabled={submittingFeedback}
                    >
                      {n}★
                    </Button>
                  ))}
                </div>
                <Textarea
                  placeholder="Optional feedback about the resolution"
                  value={feedbackComment}
                  onChange={(e) => setFeedbackComment(e.target.value)}
                  className="input-focus"
                  disabled={submittingFeedback}
                />
                <Button
                  type="button"
                  className="w-full md:w-auto"
                  disabled={!feedbackRating || submittingFeedback}
                  onClick={handleSubmitFeedback}
                >
                  {submittingFeedback ? "Submitting..." : "Submit Feedback"}
                </Button>
                {typeof issue.average_feedback_rating === "number" &&
                  (issue.feedback_count || 0) > 0 && (
                    <p className="text-xs text-muted-foreground">
                      Current average rating for this issue:{" "}
                      <span className="font-medium">
                        {issue.average_feedback_rating.toFixed(1)}★
                      </span>{" "}
                      based on {issue.feedback_count} rating
                      {issue.feedback_count === 1 ? "" : "s"}.
                    </p>
                  )}
              </div>
            )}

          {/* Reporter Info */}
          <div className="rounded-xl border bg-card p-6 space-y-4">
            <h3 className="font-semibold">Reporter</h3>
            <div className="flex items-center gap-3">
              <Avatar className="h-12 w-12">
                {issue.is_anonymous ? (
                  <AvatarFallback>AN</AvatarFallback>
                ) : issue.reporter.avatar ? (
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
                  {issue.is_anonymous
                    ? "Anonymous User"
                    : `${issue.reporter.first_name} ${issue.reporter.last_name}`}
                </p>
                {!issue.is_anonymous && (
                  <p className="text-sm text-muted-foreground">
                    {issue.reporter.student_id}
                  </p>
                )}
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
