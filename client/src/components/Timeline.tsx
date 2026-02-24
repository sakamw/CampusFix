import React from "react";
import {
  Clock,
  User,
  Wrench,
  TrendingUp,
  CheckCircle,
  AlertCircle,
  FileText,
  Calendar,
} from "lucide-react";

interface TimelineEvent {
  id: string;
  type:
    | "issue_created"
    | "work_log"
    | "progress_update"
    | "status_change"
    | "evidence_uploaded"
    | "issue_resolved";
  title: string;
  description: string;
  timestamp: string;
  user: {
    first_name: string;
    last_name: string;
    email: string;
  };
  metadata?: {
    work_type?: string;
    progress_percentage?: number;
    hours_spent?: number;
    file_type?: string;
    old_status?: string;
    new_status?: string;
  };
}

interface TimelineProps {
  events: TimelineEvent[];
}

const Timeline: React.FC<TimelineProps> = ({ events }) => {
  const getEventIcon = (type: TimelineEvent["type"]) => {
    switch (type) {
      case "issue_created":
        return <Calendar className="h-4 w-4" />;
      case "work_log":
        return <Wrench className="h-4 w-4" />;
      case "progress_update":
        return <TrendingUp className="h-4 w-4" />;
      case "status_change":
        return <AlertCircle className="h-4 w-4" />;
      case "evidence_uploaded":
        return <FileText className="h-4 w-4" />;
      case "issue_resolved":
        return <CheckCircle className="h-4 w-4" />;
      default:
        return <Clock className="h-4 w-4" />;
    }
  };

  const getEventColor = (type: TimelineEvent["type"]) => {
    switch (type) {
      case "issue_created":
        return "bg-blue-100 text-blue-700 border-blue-200";
      case "work_log":
        return "bg-orange-100 text-orange-700 border-orange-200";
      case "progress_update":
        return "bg-green-100 text-green-700 border-green-200";
      case "status_change":
        return "bg-yellow-100 text-yellow-700 border-yellow-200";
      case "evidence_uploaded":
        return "bg-purple-100 text-purple-700 border-purple-200";
      case "issue_resolved":
        return "bg-emerald-100 text-emerald-700 border-emerald-200";
      default:
        return "bg-gray-100 text-gray-700 border-gray-200";
    }
  };

  const formatDate = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  if (events.length === 0) {
    return (
      <div className="rounded-xl border bg-card p-6">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Clock className="h-5 w-5" />
          Timeline
        </h2>
        <div className="text-muted-foreground text-center py-8">
          No timeline events yet.
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border bg-card p-6">
      <h2 className="text-lg font-semibold mb-6 flex items-center gap-2">
        <Clock className="h-5 w-5" />
        Timeline
      </h2>

      <div className="relative">
        {/* Timeline line */}
        <div className="absolute left-4 top-8 bottom-0 w-0.5 bg-border"></div>

        <div className="space-y-6">
          {events.map((event, index) => (
            <div key={event.id} className="relative flex gap-4">
              {/* Timeline dot */}
              <div
                className={`relative z-10 flex h-8 w-8 items-center justify-center rounded-full border ${getEventColor(event.type)}`}
              >
                {getEventIcon(event.type)}
              </div>

              {/* Event content */}
              <div className="flex-1 pb-8">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <h3 className="font-medium text-sm">{event.title}</h3>
                    <p className="text-muted-foreground text-sm mt-1">
                      {event.description}
                    </p>

                    {/* Metadata */}
                    {event.metadata && (
                      <div className="mt-2 flex flex-wrap gap-2">
                        {event.metadata.work_type && (
                          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-muted">
                            {event.metadata.work_type}
                          </span>
                        )}
                        {event.metadata.progress_percentage !== undefined && (
                          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-muted">
                            {event.metadata.progress_percentage}% progress
                          </span>
                        )}
                        {event.metadata.hours_spent && (
                          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-muted">
                            {event.metadata.hours_spent}h spent
                          </span>
                        )}
                        {event.metadata.old_status &&
                          event.metadata.new_status && (
                            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-muted">
                              {event.metadata.old_status} →{" "}
                              {event.metadata.new_status}
                            </span>
                          )}
                      </div>
                    )}
                  </div>

                  <div className="text-right">
                    <p className="text-xs text-muted-foreground whitespace-nowrap">
                      {formatDate(event.timestamp)}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
                      <User className="h-3 w-3" />
                      {event.user.first_name} {event.user.last_name}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Timeline;
