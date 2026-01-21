import { Link } from "react-router-dom";
import {
  FileText,
  AlertCircle,
  CheckCircle2,
  Clock,
  PlusCircle,
  TrendingUp,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { StatCard } from "@/components/dashboard/StatCard";
import { IssueTable } from "@/components/dashboard/IssueTable";

const recentIssues = [
  {
    id: "ISS-001",
    title: "Broken AC unit in Lecture Hall B",
    category: "Facilities",
    status: "open" as const,
    priority: "high" as const,
    location: "Building A, Room 201",
    createdAt: "Jan 5, 2026",
    upvotes: 12,
  },
  {
    id: "ISS-002",
    title: "Wi-Fi connectivity issues in Library",
    category: "IT Infrastructure",
    status: "in-progress" as const,
    priority: "critical" as const,
    location: "Main Library, Floor 2",
    createdAt: "Jan 4, 2026",
    upvotes: 45,
  },
  {
    id: "ISS-003",
    title: "Water leak in bathroom",
    category: "Plumbing",
    status: "resolved" as const,
    priority: "medium" as const,
    location: "Student Center",
    createdAt: "Jan 3, 2026",
    upvotes: 8,
  },
  {
    id: "ISS-004",
    title: "Faulty projector in Room 305",
    category: "Equipment",
    status: "open" as const,
    priority: "low" as const,
    location: "Building C, Room 305",
    createdAt: "Jan 2, 2026",
    upvotes: 3,
  },
];

export default function Dashboard() {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">
            Welcome back! Here's an overview of your reported issues.
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
          value={24}
          description="All time reported"
          icon={FileText}
          variant="primary"
        />
        <StatCard
          title="Open Issues"
          value={8}
          description="Awaiting resolution"
          icon={AlertCircle}
          trend={{ value: 12, isPositive: false }}
        />
        <StatCard
          title="In Progress"
          value={5}
          description="Currently being addressed"
          icon={Clock}
          variant="warning"
        />
        <StatCard
          title="Resolved"
          value={11}
          description="Successfully completed"
          icon={CheckCircle2}
          trend={{ value: 23, isPositive: true }}
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
            <p className="text-2xl font-bold text-primary">87.5%</p>
          </div>
          <div className="ml-auto text-right">
            <p className="text-sm text-muted-foreground">Average Response Time</p>
            <p className="text-lg font-semibold">18 hours</p>
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
        <IssueTable issues={recentIssues} />
      </div>
    </div>
  );
}
