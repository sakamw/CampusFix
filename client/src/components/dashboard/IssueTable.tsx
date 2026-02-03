import { Link } from "react-router-dom";
import { Eye, MoreHorizontal } from "lucide-react";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../components/ui/table";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "../../components/ui/dropdown-menu";
import { Issue } from "../../lib/api";

interface IssueTableProps {
  issues: Issue[];
  showActions?: boolean;
}

// Helper function to format date
const formatDate = (dateString: string | null | undefined): string => {
  if (!dateString) return "-";
  const date = new Date(dateString);
  if (isNaN(date.getTime())) return "-";
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(date);
};

// Helper function to format category
const formatCategory = (category: string): string => {
  return category
    .split("-")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
};

const statusVariants = {
  open: "info",
  "in-progress": "warning",
  resolved: "success",
  closed: "secondary",
} as const;

const priorityVariants = {
  low: "secondary",
  medium: "info",
  high: "warning",
  critical: "destructive",
} as const;

export function IssueTable({ issues, showActions = true }: IssueTableProps) {
  return (
    <div className="rounded-lg border bg-card">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className="table-header">Issue</TableHead>
            <TableHead className="table-header">Category</TableHead>
            <TableHead className="table-header">Status</TableHead>
            <TableHead className="table-header">Priority</TableHead>
            <TableHead className="table-header">Location</TableHead>
            <TableHead className="table-header">Date</TableHead>
            {showActions && (
              <TableHead className="table-header text-right">Actions</TableHead>
            )}
          </TableRow>
        </TableHeader>
        <TableBody>
          {issues.map((issue) => (
            <TableRow key={issue.id} className="animate-fade-in">
              <TableCell>
                <Link
                  to={`/issues/${issue.id}`}
                  className="font-medium text-foreground hover:text-primary hover:underline"
                >
                  {issue.title}
                </Link>
                <p className="text-sm text-muted-foreground">#{issue.id}</p>
              </TableCell>
              <TableCell className="text-muted-foreground">
                {formatCategory(issue.category)}
              </TableCell>
              <TableCell>
                <Badge variant={statusVariants[issue.status]}>
                  {issue.status.replace("-", " ")}
                </Badge>
              </TableCell>
              <TableCell>
                <Badge variant={priorityVariants[issue.priority]}>
                  {issue.priority}
                </Badge>
              </TableCell>
              <TableCell className="text-muted-foreground">
                {issue.location}
              </TableCell>
              <TableCell className="text-muted-foreground">
                {formatDate(issue.created_at)}
              </TableCell>
              {showActions && (
                <TableCell className="text-right">
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon">
                        <MoreHorizontal className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem asChild>
                        <Link to={`/issues/${issue.id}`}>
                          <Eye className="mr-2 h-4 w-4" />
                          View Details
                        </Link>
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </TableCell>
              )}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
