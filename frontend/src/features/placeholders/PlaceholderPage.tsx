import { Clock3 } from "lucide-react";

interface PlaceholderPageProps {
  title: string;
  description: string;
}

export function PlaceholderPage({ title, description }: PlaceholderPageProps) {
  return (
    <section className="rounded-lg border border-dashed border-slate-300 bg-white p-8 text-center dark:border-slate-700 dark:bg-slate-900">
      <Clock3 className="mx-auto mb-3 text-slate-500 dark:text-slate-300" size={28} />
      <h2 className="text-lg font-semibold">{title}</h2>
      <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{description}</p>
    </section>
  );
}
