/**
 * EmptyState — displayed when no devices exist in the inventory.
 */
import { Monitor, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";

interface EmptyStateProps {
  onAdd: () => void;
}

export function EmptyState({ onAdd }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-dashed p-12 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted">
        <Monitor className="h-8 w-8 text-muted-foreground" />
      </div>
      <h3 className="mt-4 text-lg font-semibold">No devices yet</h3>
      <p className="mt-2 text-sm text-muted-foreground">
        Add your first device to start monitoring firmware updates.
      </p>
      <Button className="mt-6" onClick={onAdd}>
        <Plus className="mr-2 h-4 w-4" />
        Add Device
      </Button>
    </div>
  );
}
