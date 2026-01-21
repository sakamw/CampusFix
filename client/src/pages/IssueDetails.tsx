import { useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  MapPin,
  Calendar,
  User,
  ThumbsUp,
  MessageSquare,
  Send,
  Clock,
  CheckCircle2,
  AlertCircle,
  Wrench,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Separator } from "@/components/ui/separator";
import { useToast } from "@/hooks/use-toast";

const issueData = {
  id: "ISS-002",
  title: "Wi-Fi connectivity issues in Library",
  description:
    "The Wi-Fi connection on the second floor of the main library has been extremely unreliable for the past week. Students are unable to access online resources and submit assignments. The issue seems to be worse during peak hours (10 AM - 2 PM).",
  category: "IT Infrastructure",
  status: "in-progress",
  priority: "critical",
  location: "Main Library, Floor 2",
  createdAt: "January 4, 2026",
  reporter: {
    name: "Sarah Johnson",
    studentId: "STU123456",
    email: "sarah.johnson@university.edu",
  },
  upvotes: 45,
  assignedTo: "IT Department - Network Team",
  timeline: [
    {
      id: 1,
      type: "created",
      title: "Issue Reported",
      description: "Issue was submitted by Sarah Johnson",
      timestamp: "Jan 4, 2026 - 9:15 AM",
      icon: AlertCircle,
    },
    {
      id: 2,
      type: "assigned",
      title: "Assigned to IT Department",
      description: "Issue assigned to Network Team for investigation",
      timestamp: "Jan 4, 2026 - 10:30 AM",
      icon: User,
    },
    {
      id: 3,
      type: "update",
      title: "Investigation Started",
      description: "Network team is on-site diagnosing the issue",
      timestamp: "Jan 4, 2026 - 2:00 PM",
      icon: Wrench,
    },
    {
      id: 4,
      type: "update",
      title: "Root Cause Identified",
      description: "Faulty access point detected. Replacement ordered.",
      timestamp: "Jan 5, 2026 - 11:00 AM",
      icon: Clock,
    },
  ],
  comments: [
    {
      id: 1,
      author: "Mike Chen",
      role: "Student",
      content:
        "I've been experiencing the same issue. It's affecting my ability to attend online lectures.",
      timestamp: "Jan 4, 2026 - 11:45 AM",
    },
    {
      id: 2,
      author: "IT Support",
      role: "Staff",
      content:
        "We've identified the issue and are working on a fix. Expected resolution within 24-48 hours.",
      timestamp: "Jan 5, 2026 - 9:00 AM",
    },
  ],
};

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
  const [upvoted, setUpvoted] = useState(false);
  const [comment, setComment] = useState("");
  const [comments, setComments] = useState(issueData.comments);

  const status = statusConfig[issueData.status as keyof typeof statusConfig];
  const priority = priorityConfig[issueData.priority as keyof typeof priorityConfig];

  const handleUpvote = () => {
    setUpvoted(!upvoted);
    toast({
      title: upvoted ? "Upvote removed" : "Issue upvoted",
      description: upvoted 
        ? "Your upvote has been removed" 
        : "Thank you for upvoting this issue",
    });
  };

  const handlePostComment = () => {
    if (!comment.trim()) return;

    const newComment = {
      id: comments.length + 1,
      author: "You",
      role: "Student",
      content: comment,
      timestamp: new Date().toLocaleString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "numeric",
        minute: "2-digit",
      }),
    };

    setComments([...comments, newComment]);
    setComment("");
    toast({
      title: "Comment posted",
      description: "Your comment has been added successfully",
    });
  };

  const handleContactSupport = () => {
    toast({
      title: "Contact Support",
      description: "Opening support contact options...",
    });
    // In a real app, this could open a modal, navigate to support page, or open email
    window.location.href = `mailto:support@campusfix.edu?subject=Support Request for Issue ${issueData.id}`;
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

      {/* Header */}
      <div className="space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Badge variant={status.variant}>{status.label}</Badge>
              <Badge variant={priority.variant}>{priority.label}</Badge>
            </div>
            <h1 className="text-3xl font-bold tracking-tight">
              {issueData.title}
            </h1>
            <p className="text-muted-foreground">#{issueData.id}</p>
          </div>

          <Button
            variant={upvoted ? "default" : "outline"}
            onClick={handleUpvote}
            className="gap-2"
          >
            <ThumbsUp className={`h-4 w-4 ${upvoted ? "fill-current" : ""}`} />
            <span>{upvoted ? issueData.upvotes + 1 : issueData.upvotes}</span>
            Upvote
          </Button>
        </div>

        <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
          <div className="flex items-center gap-1">
            <MapPin className="h-4 w-4" />
            {issueData.location}
          </div>
          <div className="flex items-center gap-1">
            <Calendar className="h-4 w-4" />
            {issueData.createdAt}
          </div>
          <div className="flex items-center gap-1">
            <User className="h-4 w-4" />
            Reported by {issueData.reporter.name}
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
              {issueData.description}
            </p>
          </div>

          {/* Timeline */}
          <div className="rounded-xl border bg-card p-6">
            <h2 className="text-lg font-semibold mb-6">Activity Timeline</h2>
            <div className="space-y-6">
              {issueData.timeline.map((event, index) => (
                <div key={event.id} className="flex gap-4">
                  <div className="relative flex flex-col items-center">
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
                      <event.icon className="h-5 w-5 text-primary" />
                    </div>
                    {index < issueData.timeline.length - 1 && (
                      <div className="absolute top-10 h-full w-px bg-border" />
                    )}
                  </div>
                  <div className="flex-1 pb-6">
                    <p className="font-medium">{event.title}</p>
                    <p className="text-sm text-muted-foreground">
                      {event.description}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {event.timestamp}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Comments */}
          <div className="rounded-xl border bg-card p-6">
            <h2 className="text-lg font-semibold mb-6 flex items-center gap-2">
              <MessageSquare className="h-5 w-5" />
              Comments ({comments.length})
            </h2>

            <div className="space-y-6">
              {comments.map((c) => (
                <div key={c.id} className="flex gap-4">
                  <Avatar>
                    <AvatarFallback>
                      {c.author
                        .split(" ")
                        .map((n) => n[0])
                        .join("")}
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <p className="font-medium">{c.author}</p>
                      <Badge variant="secondary" className="text-xs">
                        {c.role}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground mt-1">
                      {c.content}
                    </p>
                    <p className="text-xs text-muted-foreground mt-2">
                      {c.timestamp}
                    </p>
                  </div>
                </div>
              ))}
            </div>

            <Separator className="my-6" />

            <div className="space-y-4">
              <Textarea
                placeholder="Add a comment..."
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                className="input-focus"
              />
              <div className="flex justify-end">
                <Button disabled={!comment.trim()} onClick={handlePostComment}>
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
                <span className="font-medium">{issueData.category}</span>
              </div>
              <Separator />
              <div className="flex justify-between">
                <span className="text-muted-foreground">Assigned To</span>
                <span className="font-medium text-right text-xs">
                  {issueData.assignedTo}
                </span>
              </div>
              <Separator />
              <div className="flex justify-between">
                <span className="text-muted-foreground">Upvotes</span>
                <span className="font-medium">{issueData.upvotes}</span>
              </div>
            </div>
          </div>

          {/* Reporter Info */}
          <div className="rounded-xl border bg-card p-6 space-y-4">
            <h3 className="font-semibold">Reporter</h3>
            <div className="flex items-center gap-3">
              <Avatar className="h-12 w-12">
                <AvatarFallback>
                  {issueData.reporter.name
                    .split(" ")
                    .map((n) => n[0])
                    .join("")}
                </AvatarFallback>
              </Avatar>
              <div>
                <p className="font-medium">{issueData.reporter.name}</p>
                <p className="text-sm text-muted-foreground">
                  {issueData.reporter.studentId}
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
            <Button variant="outline" className="w-full" onClick={handleContactSupport}>
              Contact Support
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
