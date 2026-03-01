import { Sparkles } from "lucide-react";
import { Link } from "react-router-dom";

export function EmptyState() {
  return (
    <section className="mt-6 rounded-lg border border-dashed border-slate-300 bg-white p-8 text-center dark:border-slate-700 dark:bg-slate-900">
      <Sparkles className="mx-auto mb-3 text-slate-500 dark:text-slate-300" size={30} />
      <h2 className="text-lg font-semibold">No devices yet</h2>
      <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
        Create your first device type, then add your first device to start tracking firmware
        updates.
      </p>
      <Link
        to="/modules"
        className="mt-4 inline-flex rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
      >
        Create Your First Device Type
      </Link>
    </section>
  );
}
