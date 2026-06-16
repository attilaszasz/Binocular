/**
 * DeviceForm — add/edit device form with module selection dropdown.
 */
import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useModules } from "@/hooks/use-modules";
import { checksApi, type Device, type DeviceCreate, type DeviceUpdate } from "@/lib/api";
import { Loader2 } from "lucide-react";

interface DeviceFormProps {
  /** When provided, the form is in edit mode. */
  device?: Device;
  onSubmit: (data: DeviceCreate | DeviceUpdate) => void;
  onCancel: () => void;
  isPending?: boolean;
}

export function DeviceForm({
  device,
  onSubmit,
  onCancel,
  isPending,
}: DeviceFormProps) {
  const { data: modules, isLoading: modulesLoading } = useModules();

  const [name, setName] = useState(device?.name ?? "");
  const [model, setModel] = useState(device?.model ?? "");
  const [moduleId, setModuleId] = useState<string>(
    device?.module_id?.toString() ?? "",
  );
  const [currentVersion, setCurrentVersion] = useState(
    device?.current_version ?? "",
  );
  const [error, setError] = useState<string | null>(null);
  const [isSearching, setIsSearching] = useState(false);

  const handleSearchVersion = async () => {
    if (!moduleId || !model.trim()) return;
    setIsSearching(true);
    setError(null);
    try {
      const result = await checksApi.searchVersion(Number(moduleId), model.trim());
      if (result.version) {
        setCurrentVersion(result.version);
      } else {
        throw new Error("No version returned by module");
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "An unexpected error occurred during version search";
      setError(message);
    } finally {
      setIsSearching(false);
    }
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!name.trim()) {
      setError("Device name is required.");
      return;
    }
    if (!moduleId) {
      setError("Please select a module.");
      return;
    }

    if (device) {
      const update: DeviceUpdate = {};
      if (name !== device.name) update.name = name;
      if (model !== device.model) update.model = model;
      if (Number(moduleId) !== device.module_id)
        update.module_id = Number(moduleId);
      if (currentVersion !== device.current_version)
        update.current_version = currentVersion;
      onSubmit(update);
    } else {
      onSubmit({
        name,
        model,
        module_id: Number(moduleId),
        current_version: currentVersion,
      } satisfies DeviceCreate);
    }
  };

  const noModules = !modulesLoading && (!modules || modules.length === 0);

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {noModules && (
        <p className="text-sm text-amber-500">
          No modules available. Add a module before registering devices.
        </p>
      )}

      {error && <p className="text-sm text-destructive">{error}</p>}

      <div className="space-y-2">
        <Label htmlFor="device-name">Name</Label>
        <Input
          id="device-name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. Main Camera"
          required
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="device-model">Model</Label>
        <Input
          id="device-model"
          value={model}
          onChange={(e) => setModel(e.target.value)}
          placeholder="e.g. A7R V"
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="device-module">Module</Label>
        <div className="flex gap-2">
          <div className="flex-1">
            <Select
              value={moduleId}
              onValueChange={setModuleId}
              disabled={noModules}
            >
              <SelectTrigger id="device-module">
                <SelectValue placeholder="Select a module" />
              </SelectTrigger>
              <SelectContent>
                {modules?.map((m) => (
                  <SelectItem key={m.id} value={m.id.toString()}>
                    {m.name} ({m.device_type})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button
            type="button"
            variant="outline"
            disabled={!moduleId || !model.trim() || isSearching}
            onClick={handleSearchVersion}
          >
            {isSearching && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {isSearching ? "Searching..." : "Search Version"}
          </Button>
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="device-version">Current Version</Label>
        <Input
          id="device-version"
          value={currentVersion}
          onChange={(e) => setCurrentVersion(e.target.value)}
          placeholder="e.g. 1.0.0"
        />
      </div>

      <div className="flex gap-2 pt-2">
        <Button type="submit" disabled={isPending || noModules}>
          {device ? "Save Changes" : "Add Device"}
        </Button>
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </form>
  );
}
