import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft,
  Clock,
  CheckCircle2,
  AlertCircle,
  MessageSquare,
  Paperclip,
  Download,
  User,
  Calendar,
  MapPin,
  Send,
  ThumbsUp,
} from "lucide-react";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Separator } from "../components/ui/separator";
import { Avatar, AvatarFallback, AvatarImage } from "../components/ui/avatar";
import { Textarea } from "../components/ui/textarea";
import { Alert, AlertDescription } from "../components/ui/alert";
import { useToast } from "../hooks/use-toast";
import { issuesApi, IssueDetail, AdminWorkLog, ResolutionEvidence, ProgressUpdate } from "../lib/api";

const statusConfig = {
  open: { variant: "info" as const, label: "Open", icon: AlertCircle },
  "in-progress": { variant: "warning" as const, label: "In Progress", icon: Clock },
  resolved: { variant: "success" as const, label: "Resolved", icon: CheckCircle2 },
  closed: { variant: "secondary" as const, label: "Closed", icon: CheckCircle2 },
};

const priorityConfig = {
  low: { variant: "secondary" as const, label: "Low" },
  medium: { variant: "info" as const, label: "Medium" },
  high: { variant: "warning" as const, label: "High" },
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

// Helper function to format date
const formatDate = (dateString: string | null | undefined): string => {
  if (!dateString) return "";
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
};

export default function IssueResponses() {
  const { toast } = useToast();
  const [issues, setIssues] = useState<IssueDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedIssue, setSelectedIssue] = useState<IssueDetail | null>(null);
  const [filter, setFilter] = useState<'all' | 'open' | 'in-progress' | 'resolved' | 'closed'>('all');
  const [chatOpen, setChatOpen] = useState<number | null>(null);
  const [commentInputs, setCommentInputs] = useState<{ [key: number]: string }>({});
  const [submittingComment, setSubmittingComment] = useState(false);

  useEffect(() => {
    fetchUserIssues();
  }, []);

  const fetchUserIssues = async () => {
    setLoading(true);
    try {
      const response = await issuesApi.getIssues({ filter: "my-issues" });
      if (response.data) {
        setIssues(response.data);
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to load your issues",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const filteredIssues = issues.filter(issue => 
    filter === 'all' || issue.status === filter
  );

  const hasAdminActivity = (issue: IssueDetail) => {
    return (issue.comments && issue.comments.some(comment => comment.user.role === 'admin')) || 
           issue.status !== 'open' ||
           (issue.evidence_files && issue.evidence_files.length > 0) ||
           issue.progress_percentage > 0 ||
           (issue.progress_updates && issue.progress_updates.length > 0);
  };

  const getAdminComments = (issue: IssueDetail) => {
    return (issue.comments || []).filter(comment => comment.user.role === 'admin');
  };

  const handleAddComment = async (issueId: number) => {
    const comment = commentInputs[issueId] || '';
    if (!comment.trim()) return;
    
    setSubmittingComment(true);
    try {
      const response = await issuesApi.addComment(issueId, comment.trim());
      if (response.data) {
        // Update the issue in the local state with the new comment
        setIssues(prevIssues => 
          prevIssues.map(issue => 
            issue.id === issueId 
              ? { ...issue, comments: [...(issue.comments || []), response.data] }
              : issue
          )
        );
        // Clear the comment input for this issue
        setCommentInputs(prev => ({ ...prev, [issueId]: '' }));
        toast({
          title: "Success",
          description: "Comment added successfully",
        });
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to add comment",
        variant: "destructive",
      });
    } finally {
      setSubmittingComment(false);
    }
  };

  const handleMarkResolved = async (issueId: number) => {
    try {
      const response = await issuesApi.updateIssue(issueId, { status: 'resolved' });
      if (response.data) {
        // Update the issue in the local state
        setIssues(prevIssues => 
          prevIssues.map(issue => 
            issue.id === issueId ? { ...issue, ...response.data } : issue
          )
        );
        toast({
          title: "Success",
          description: "Issue marked as resolved. Thank you for your feedback!",
        });
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to update issue status",
        variant: "destructive",
      });
    }
  };

  if (loading) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" asChild>
          <Link to="/dashboard">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Issue Responses</h1>
          <p className="text-muted-foreground">
            Track admin responses and progress on your reported issues
          </p>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2 flex-wrap">
        {(['all', 'open', 'in-progress', 'resolved', 'closed'] as const).map((status) => (
          <Button
            key={status}
            variant={filter === status ? "default" : "outline"}
            size="sm"
            onClick={() => setFilter(status)}
          >
            {status === 'all' ? 'All Issues' : status.replace('-', ' ').replace(/\b\w/g, l => l.toUpperCase())}
            <span className="ml-2 text-xs">
              ({status === 'all' ? issues.length : issues.filter(i => i.status === status).length})
            </span>
          </Button>
        ))}
      </div>

      {/* Issues List */}
      <div className="space-y-4">
        {filteredIssues.length === 0 ? (
          <Card>
            <CardContent className="p-8 text-center">
              <AlertCircle className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">No issues found</h3>
              <p className="text-muted-foreground">
                {filter === 'all' 
                  ? "You haven't reported any issues yet." 
                  : `No issues with status "${filter.replace('-', ' ')}".`}
              </p>
              <Button className="mt-4" asChild>
                <Link to="/report">Report New Issue</Link>
              </Button>
            </CardContent>
          </Card>
        ) : (
          filteredIssues.map((issue) => (
            <Card key={issue.id} className="overflow-hidden">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <CardTitle className="text-lg">{issue.title}</CardTitle>
                      <Badge variant={statusConfig[issue.status].variant}>
                        {statusConfig[issue.status].label}
                      </Badge>
                      <Badge variant={priorityConfig[issue.priority].variant}>
                        {priorityConfig[issue.priority].label}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <MapPin className="h-4 w-4" />
                        {issue.location}
                      </span>
                      <span className="flex items-center gap-1">
                        <Calendar className="h-4 w-4" />
                        {formatDate(issue.created_at)}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {hasAdminActivity(issue) && (
                      <Badge variant="secondary" className="bg-green-100 text-green-800">
                        Admin Response
                      </Badge>
                    )}
                    <Button variant="outline" size="sm" asChild>
                      <Link to={`/issues/${issue.id}`}>View Details</Link>
                    </Button>
                  </div>
                </div>
              </CardHeader>
              
              {/* Admin Activity Summary */}
              {hasAdminActivity(issue) && (
                <CardContent className="border-t bg-muted/30">
                  <div className="space-y-4">
                    {/* Progress Tracking */}
                    {(issue.progress_percentage > 0 || (issue.progress_updates && issue.progress_updates.length > 0)) && (
                      <div className="space-y-3">
                        <div className="flex items-center gap-2">
                          <div className="w-4 h-4 rounded-full bg-blue-500"></div>
                          <p className="font-medium">Progress Tracking</p>
                          <Badge variant="secondary" className="bg-blue-100 text-blue-800">
                            {issue.progress_percentage || 0}% Complete
                          </Badge>
                        </div>
                        
                        {/* Progress Bar */}
                        <div className="space-y-2">
                          <div className="w-full bg-gray-200 rounded-full h-2">
                            <div 
                              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                              style={{ width: `${issue.progress_percentage || 0}%` }}
                            ></div>
                          </div>
                          <div className="flex justify-between text-xs text-muted-foreground">
                            <span>Progress: {issue.progress_percentage || 0}%</span>
                            <span>Status: {issue.progress_status || 'Not started'}</span>
                          </div>
                        </div>

                        {/* Progress Updates */}
                        {issue.progress_updates && issue.progress_updates.length > 0 && (
                          <div className="space-y-2">
                            <p className="text-sm font-medium">Recent Updates:</p>
                            {issue.progress_updates.slice(0, 2).map((update) => (
                              <div key={update.id} className="p-2 bg-blue-50 border-l-4 border-blue-500 rounded">
                                <div className="flex items-center gap-2 mb-1">
                                  <p className="text-sm font-medium">{update.title}</p>
                                  <Badge variant="outline" className="text-xs">
                                    {update.progress_percentage}%
                                  </Badge>
                                  {update.is_major_update && (
                                    <Badge variant="secondary" className="text-xs bg-yellow-100 text-yellow-800">
                                      Major Milestone
                                    </Badge>
                                  )}
                                </div>
                                <p className="text-xs text-muted-foreground mb-1">{update.description}</p>
                                <p className="text-xs text-muted-foreground">
                                  {update.update_type} • {formatDate(update.created_at)}
                                </p>
                                {update.next_steps && (
                                  <p className="text-xs text-blue-600 mt-1">
                                    Next: {update.next_steps}
                                  </p>
                                )}
                              </div>
                            ))}
                            {issue.progress_updates.length > 2 && (
                              <Button variant="ghost" size="sm" className="text-xs">
                                View all {issue.progress_updates.length} updates
                              </Button>
                            )}
                          </div>
                        )}

                        {/* Progress Notes */}
                        {issue.progress_notes && (
                          <div className="p-2 bg-gray-50 rounded">
                            <p className="text-sm text-gray-700">{issue.progress_notes}</p>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Status Progress */}
                    {issue.status !== 'open' && (
                      <div className="flex items-center gap-3">
                        <div className={`p-2 rounded-full ${statusConfig[issue.status].variant === 'success' ? 'bg-green-100' : 'bg-yellow-100'}`}>
                          {statusConfig[issue.status].icon && 
                            React.createElement(statusConfig[issue.status].icon, {
                              className: `h-4 w-4 ${statusConfig[issue.status].variant === 'success' ? 'text-green-600' : 'text-yellow-600'}`
                            })
                          }
                        </div>
                        <div>
                          <p className="font-medium">Status Updated</p>
                          <p className="text-sm text-muted-foreground">
                            Issue is currently {statusConfig[issue.status].label.toLowerCase()}
                          </p>
                        </div>
                      </div>
                    )}

                    {/* Admin Comments */}
                    {getAdminComments(issue).length > 0 && (
                      <div className="space-y-3">
                        <div className="flex items-center gap-2">
                          <MessageSquare className="h-4 w-4" />
                          <p className="font-medium">Admin Comments ({getAdminComments(issue).length})</p>
                        </div>
                        {getAdminComments(issue).slice(0, 2).map((comment) => (
                          <div key={comment.id} className="flex gap-3 p-3 bg-background rounded-lg border">
                            <Avatar className="h-8 w-8">
                              <AvatarFallback className="text-xs bg-primary text-primary-foreground">
                                {comment.user.first_name?.[0] || "A"}
                              </AvatarFallback>
                            </Avatar>
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-1">
                                <p className="text-sm font-medium">
                                  {comment.user.first_name} {comment.user.last_name}
                                </p>
                                <Badge variant="secondary" className="text-xs">
                                  Admin
                                </Badge>
                                <span className="text-xs text-muted-foreground">
                                  {formatDate(comment.created_at)}
                                </span>
                              </div>
                              <p className="text-sm">{comment.content}</p>
                            </div>
                          </div>
                        ))}
                        {getAdminComments(issue).length > 2 && (
                          <Button variant="ghost" size="sm" className="text-xs">
                            View all {getAdminComments(issue).length} comments
                          </Button>
                        )}
                      </div>
                    )}

                    {/* Evidence Files */}
                    {issue.evidence_files && issue.evidence_files.length > 0 && (
                      <div className="space-y-3">
                        <div className="flex items-center gap-2">
                          <Paperclip className="h-4 w-4" />
                          <p className="font-medium">Evidence Files ({issue.evidence_files.length})</p>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                          {issue.evidence_files.slice(0, 3).map((evidence) => (
                            <div key={evidence.id} className="flex items-center gap-2 p-2 bg-background rounded border text-sm">
                              <Paperclip className="h-3 w-3 text-muted-foreground" />
                              <a 
                                href={evidence.file} 
                                target="_blank" 
                                rel="noopener noreferrer"
                                className="hover:text-primary hover:underline truncate"
                              >
                                {evidence.filename}
                              </a>
                              <span className="text-xs text-muted-foreground ml-auto">
                                {formatFileSize(evidence.file_size)}
                              </span>
                            </div>
                          ))}
                        </div>
                        {issue.evidence_files.length > 3 && (
                          <Button variant="ghost" size="sm" className="text-xs">
                            View all {issue.evidence_files.length} files
                          </Button>
                        )}
                      </div>
                    )}

                    {/* Resolution Summary */}
                    {(issue.status === 'resolved' || issue.status === 'closed') && issue.resolution_summary && (
                      <div className="space-y-2 p-3 bg-green-50 border border-green-200 rounded-lg">
                        <div className="flex items-center gap-2">
                          <CheckCircle2 className="h-4 w-4 text-green-600" />
                          <p className="font-medium text-green-800">Resolution Summary</p>
                        </div>
                        <p className="text-sm text-green-700">{issue.resolution_summary}</p>
                      </div>
                    )}
                  </div>
                </CardContent>
              )}
              
              {/* Chat Interface */}
              <CardContent className="border-t bg-muted/20">
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <MessageSquare className="h-4 w-4" />
                      <p className="font-medium">Chat with Admin</p>
                      <Badge variant="secondary" className="text-xs">
                        {(issue.comments || []).length} messages
                      </Badge>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setChatOpen(chatOpen === issue.id ? null : issue.id)}
                    >
                      {chatOpen === issue.id ? 'Hide' : 'Show'}
                    </Button>
                  </div>
                  
                  {chatOpen === issue.id && (
                    <div className="space-y-4">
                      {/* Comments Display */}
                      <div className="space-y-3 max-h-60 overflow-y-auto">
                        {(issue.comments || []).length === 0 ? (
                          <p className="text-sm text-muted-foreground text-center py-4">
                            No comments yet. Start the conversation!
                          </p>
                        ) : (
                          (issue.comments || []).map((comment) => (
                            <div key={comment.id} className="flex gap-3 p-3 bg-background rounded-lg border">
                              <Avatar className="h-8 w-8">
                                <AvatarFallback className="text-xs bg-primary text-primary-foreground">
                                  {comment.user.first_name?.[0] || "U"}
                                </AvatarFallback>
                              </Avatar>
                              <div className="flex-1">
                                <div className="flex items-center gap-2 mb-1">
                                  <p className="text-sm font-medium">
                                    {comment.user.first_name} {comment.user.last_name}
                                  </p>
                                  {comment.user.role === 'admin' && (
                                    <Badge variant="secondary" className="text-xs">
                                      Admin
                                    </Badge>
                                  )}
                                  <span className="text-xs text-muted-foreground">
                                    {formatDate(comment.created_at)}
                                  </span>
                                </div>
                                <p className="text-sm">{comment.content}</p>
                              </div>
                            </div>
                          ))
                        )}
                      </div>
                      
                      {/* Add Comment Form */}
                      <div className="space-y-3">
                        <Textarea
                          placeholder="Type your message here..."
                          value={commentInputs[issue.id] || ''}
                          onChange={(e) => setCommentInputs(prev => ({ ...prev, [issue.id]: e.target.value }))}
                          className="min-h-[80px]"
                          disabled={submittingComment}
                        />
                        <div className="flex gap-2">
                          <Button
                            onClick={() => handleAddComment(issue.id)}
                            disabled={!commentInputs[issue.id]?.trim() || submittingComment}
                            size="sm"
                          >
                            <Send className="h-4 w-4 mr-2" />
                            {submittingComment ? 'Sending...' : 'Send'}
                          </Button>
                          
                          {/* Mark as Resolved Button - only show if issue is not already resolved */}
                          {issue.status !== 'resolved' && issue.status !== 'closed' && (
                            <Button
                              variant="outline"
                              onClick={() => handleMarkResolved(issue.id)}
                              size="sm"
                              className="ml-auto"
                            >
                              <ThumbsUp className="h-4 w-4 mr-2" />
                              Mark as Resolved
                            </Button>
                          )}
                        </div>
                      </div>
                      
                      {/* Success Message for Resolved Issues */}
                      {(issue.status === 'resolved' || issue.status === 'closed') && (
                        <Alert>
                          <CheckCircle2 className="h-4 w-4" />
                          <AlertDescription>
                            This issue has been marked as {issue.status}. Thank you for your feedback!
                          </AlertDescription>
                        </Alert>
                      )}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
