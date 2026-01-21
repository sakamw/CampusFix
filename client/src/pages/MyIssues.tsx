import { Link } from "react-router-dom";
import { PlusCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { IssueTable } from "@/components/dashboard/IssueTable";

// My reported issues - In a real app, this would be fetched from the API filtered by current user
const myIssues = [
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
    title: "Broken door handle in Library entrance",
    category: "Facilities",
    status: "in-progress" as const,
    priority: "medium" as const,
    location: "Main Library",
    createdAt: "Jan 1, 2026",
    upvotes: 15,
  },
];

export default function MyIssues() {
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
      {myIssues.length > 0 ? (
        <IssueTable issues={myIssues} />
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

