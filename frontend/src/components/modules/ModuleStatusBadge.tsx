import { Badge } from "@/components/ui/badge";

interface ModuleStatusBadgeProps {
  status: string;
}

export function ModuleStatusBadge({ status }: ModuleStatusBadgeProps) {
  switch (status) {
    case "active":
      return (
        <Badge className="bg-emerald-500/10 text-emerald-600 hover:bg-emerald-500/20 border-emerald-500/20 dark:bg-emerald-500/20 dark:text-emerald-400">
          active
        </Badge>
      );
    case "inactive":
      return (
        <Badge variant="secondary">
          inactive
        </Badge>
      );
    case "error":
      return (
        <Badge variant="destructive">
          error
        </Badge>
      );
    default:
      return (
        <Badge variant="outline">
          {status}
        </Badge>
      );
  }
}
