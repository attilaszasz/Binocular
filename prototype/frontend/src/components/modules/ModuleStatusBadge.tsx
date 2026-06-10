import type { InstalledModule } from '@/api';
import { Badge } from '@/components/ui/badge';

export function ModuleStatusBadge({ status }: { status: InstalledModule['validationStatus'] }) {
  switch (status) {
    case 'valid':
      return (
        <Badge
          variant="default"
          className="border border-emerald-200 bg-emerald-50 text-emerald-600 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-400"
        >
          {status}
        </Badge>
      );
    case 'invalid':
      return <Badge variant="destructive">{status}</Badge>;
    default:
      return <Badge variant="secondary">{status}</Badge>;
  }
}
