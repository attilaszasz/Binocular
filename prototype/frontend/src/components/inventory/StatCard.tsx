import { type LucideIcon } from 'lucide-react';

import { Card, CardContent } from '@/components/ui/card';

interface StatCardProps {
  label: string;
  value: number;
  icon: LucideIcon;
  tone: 'indigo' | 'rose' | 'emerald';
}

export function StatCard({ label, value, icon: Icon, tone }: StatCardProps) {
  const toneClass = {
    indigo:
      'bg-sky-100 text-sky-700 ring-1 ring-sky-200 dark:bg-sky-500/15 dark:text-sky-300 dark:ring-sky-400/20',
    rose:
      'bg-rose-100 text-rose-700 ring-1 ring-rose-200 dark:bg-rose-500/15 dark:text-rose-300 dark:ring-rose-400/20',
    emerald:
      'bg-emerald-100 text-emerald-700 ring-1 ring-emerald-200 dark:bg-emerald-500/15 dark:text-emerald-300 dark:ring-emerald-400/20',
  }[tone];

  const cardClass = {
    indigo:
      'border-sky-200/80 bg-gradient-to-br from-white via-sky-50/80 to-sky-100/70 dark:border-sky-400/20 dark:from-card dark:via-sky-500/10 dark:to-sky-500/5',
    rose:
      'border-rose-200/80 bg-gradient-to-br from-white via-rose-50/80 to-rose-100/70 dark:border-rose-400/20 dark:from-card dark:via-rose-500/10 dark:to-rose-500/5',
    emerald:
      'border-emerald-200/80 bg-gradient-to-br from-white via-emerald-50/80 to-emerald-100/70 dark:border-emerald-400/20 dark:from-card dark:via-emerald-500/10 dark:to-emerald-500/5',
  }[tone];

  return (
    <Card className={cardClass}>
      <CardContent className="p-5">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-muted-foreground">{label}</p>
            <p className="mt-2 text-3xl font-bold">{value}</p>
          </div>
          <div className={`rounded-xl p-3 ${toneClass}`}>
            <Icon size={24} />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
