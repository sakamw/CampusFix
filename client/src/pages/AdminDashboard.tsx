import { useState } from "react";
import {
  FileText,
  AlertCircle,
  CheckCircle2,
  Clock,
  Users,
  TrendingUp,
  TrendingDown,
  Filter,
  Download,
  BarChart3,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { StatCard } from "@/components/dashboard/StatCard";
import { IssueTable } from "@/components/dashboard/IssueTable";

const allIssues = [
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
  {
    id: "ISS-005",
    title: "Elevator out of service",
    category: "Facilities",
    status: "in-progress" as const,
    priority: "high" as const,
    location: "Building B",
    createdAt: "Jan 2, 2026",
    upvotes: 28,
  },
  {
    id: "ISS-006",
    title: "Broken window in common area",
    category: "Facilities",
    status: "closed" as const,
    priority: "medium" as const,
    location: "Student Center",
    createdAt: "Jan 1, 2026",
    upvotes: 5,
  },
];

const analyticsData = {
  categoryBreakdown: [
    { name: "Facilities", count: 45, percentage: 35 },
    { name: "IT Infrastructure", count: 32, percentage: 25 },
    { name: "Plumbing", count: 19, percentage: 15 },
    { name: "Equipment", count: 16, percentage: 12 },
    { name: "Other", count: 17, percentage: 13 },
  ],
  weeklyTrend: [
    { day: "Mon", issues: 12 },
    { day: "Tue", issues: 8 },
    { day: "Wed", issues: 15 },
    { day: "Thu", issues: 10 },
    { day: "Fri", issues: 18 },
    { day: "Sat", issues: 4 },
    { day: "Sun", issues: 2 },
  ],
};

export default function AdminDashboard() {
  const [statusFilter, setStatusFilter] = useState("all");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");

  const handleExportReport = () => {
    // TODO: Implement export functionality
    console.log("Exporting report...");
  };

  const handleViewCriticalIssues = () => {
    // TODO: Navigate to critical issues or filter
    setStatusFilter("open");
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Admin Dashboard</h1>
          <p className="text-muted-foreground">
            Manage and monitor all campus issues in one place.
          </p>
        </div>
        <Button variant="outline" onClick={handleExportReport}>
          <Download className="mr-2 h-4 w-4" />
          Export Report
        </Button>
      </div>

      {/* KPI Stats */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
        <StatCard
          title="Total Issues"
          value={129}
          description="This month"
          icon={FileText}
          trend={{ value: 8, isPositive: false }}
        />
        <StatCard title="Open" value={34} icon={AlertCircle} />
        <StatCard
          title="In Progress"
          value={28}
          icon={Clock}
          variant="warning"
        />
        <StatCard
          title="Resolved"
          value={67}
          icon={CheckCircle2}
          trend={{ value: 15, isPositive: true }}
          variant="success"
        />
        <StatCard
          title="Active Users"
          value="2,847"
          description="Reporting issues"
          icon={Users}
          variant="primary"
        />
      </div>

      {/* Quick Stats Row */}
      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-xl border bg-card p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">
                Avg. Resolution Time
              </p>
              <p className="text-2xl font-bold">18h 24m</p>
            </div>
            <div className="flex items-center gap-1 text-success text-sm font-medium">
              <TrendingDown className="h-4 w-4" />
              12% faster
            </div>
          </div>
        </div>
        <div className="rounded-xl border bg-card p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">
                Student Satisfaction
              </p>
              <p className="text-2xl font-bold">94.2%</p>
            </div>
            <div className="flex items-center gap-1 text-success text-sm font-medium">
              <TrendingUp className="h-4 w-4" />
              +2.4%
            </div>
          </div>
        </div>
        <div className="rounded-xl border bg-card p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Critical Issues</p>
              <p className="text-2xl font-bold text-destructive">3</p>
            </div>
            <Button
              size="sm"
              variant="destructive"
              onClick={handleViewCriticalIssues}
            >
              View All
            </Button>
          </div>
        </div>
      </div>

      {/* Main Content Tabs */}
      <Tabs defaultValue="issues" className="space-y-6">
        <TabsList>
          <TabsTrigger value="issues">All Issues</TabsTrigger>
          <TabsTrigger value="analytics">Analytics</TabsTrigger>
        </TabsList>

        <TabsContent value="issues" className="space-y-6">
          {/* Filters */}
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium">Filters:</span>
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="open">Open</SelectItem>
                <SelectItem value="in-progress">In Progress</SelectItem>
                <SelectItem value="resolved">Resolved</SelectItem>
                <SelectItem value="closed">Closed</SelectItem>
              </SelectContent>
            </Select>
            <Select value={categoryFilter} onValueChange={setCategoryFilter}>
              <SelectTrigger className="w-48">
                <SelectValue placeholder="Category" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Categories</SelectItem>
                <SelectItem value="facilities">Facilities</SelectItem>
                <SelectItem value="it">IT Infrastructure</SelectItem>
                <SelectItem value="plumbing">Plumbing</SelectItem>
                <SelectItem value="equipment">Equipment</SelectItem>
              </SelectContent>
            </Select>
            <Input
              placeholder="Search issues..."
              className="w-64"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          {/* Issues Table */}
          <div data-issues-table>
            <IssueTable
              issues={allIssues.filter((issue) => {
                if (
                  searchQuery &&
                  !issue.title
                    .toLowerCase()
                    .includes(searchQuery.toLowerCase()) &&
                  !issue.id.toLowerCase().includes(searchQuery.toLowerCase())
                ) {
                  return false;
                }
                if (statusFilter !== "all" && issue.status !== statusFilter) {
                  return false;
                }
                if (
                  categoryFilter !== "all" &&
                  issue.category.toLowerCase() !== categoryFilter
                ) {
                  return false;
                }
                return true;
              })}
            />
          </div>
        </TabsContent>

        <TabsContent value="analytics" className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Category Breakdown */}
            <div className="rounded-xl border bg-card p-6">
              <h3 className="text-lg font-semibold mb-6 flex items-center gap-2">
                <BarChart3 className="h-5 w-5 text-primary" />
                Issues by Category
              </h3>
              <div className="space-y-4">
                {analyticsData.categoryBreakdown.map((cat) => (
                  <div key={cat.name} className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <span>{cat.name}</span>
                      <span className="font-medium">{cat.count} issues</span>
                    </div>
                    <div className="h-2 rounded-full bg-muted overflow-hidden">
                      <div
                        className="h-full rounded-full bg-primary transition-all"
                        style={{ width: `${cat.percentage}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Weekly Trend */}
            <div className="rounded-xl border bg-card p-6">
              <h3 className="text-lg font-semibold mb-6">Weekly Issue Trend</h3>
              <div className="flex items-end justify-between h-48 gap-2">
                {analyticsData.weeklyTrend.map((day) => (
                  <div
                    key={day.day}
                    className="flex flex-col items-center gap-2 flex-1"
                  >
                    <div
                      className="w-full bg-primary/20 rounded-t transition-all hover:bg-primary/30"
                      style={{ height: `${(day.issues / 20) * 100}%` }}
                    >
                      <div
                        className="w-full bg-primary rounded-t"
                        style={{ height: `${(day.issues / 20) * 100}%` }}
                      />
                    </div>
                    <span className="text-xs text-muted-foreground">
                      {day.day}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Performance Metrics */}
          <div className="rounded-xl border bg-card p-6">
            <h3 className="text-lg font-semibold mb-6">
              Department Performance
            </h3>
            <div className="grid gap-4 md:grid-cols-4">
              {[
                { dept: "Facilities", resolved: 45, pending: 12, rate: "78%" },
                { dept: "IT Support", resolved: 32, pending: 8, rate: "80%" },
                { dept: "Plumbing", resolved: 19, pending: 5, rate: "79%" },
                { dept: "Security", resolved: 28, pending: 3, rate: "90%" },
              ].map((dept) => (
                <div
                  key={dept.dept}
                  className="rounded-lg border bg-muted/30 p-4 space-y-2"
                >
                  <p className="font-medium">{dept.dept}</p>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Resolved</span>
                    <span className="text-success font-medium">
                      {dept.resolved}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Pending</span>
                    <span className="text-warning font-medium">
                      {dept.pending}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm pt-2 border-t">
                    <span className="text-muted-foreground">
                      Resolution Rate
                    </span>
                    <span className="font-bold">{dept.rate}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
