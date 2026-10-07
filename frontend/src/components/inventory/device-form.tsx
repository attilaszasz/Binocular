/**
 * DeviceForm — add/edit device form with module selection dropdown.
 */
import { useEffect, useRef, useState, type FormEvent } from "react";
import { SourceGuidance } from "./SourceGuidance";
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
  const { data: modules, isLoading: modulesLoading, isError: modulesError } = useModules();

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
  const generation = useRef(0);
  const derivedVersion = useRef(false);
  useEffect(() => () => { generation.current++; }, []);
  const resetSearch = () => {
    generation.current++;
    setIsSearching(false);
    setError(null);
    if (derivedVersion.current) setCurrentVersion("");
    derivedVersion.current = false;
  };

  const handleSearchVersion = async () => {
    if (!moduleId || !model.trim()) return;
    const requestGeneration = ++generation.current;
    setIsSearching(true);
    setError(null);
    try {
      const result = await checksApi.searchVersion(Number(moduleId), model.trim());
      if (requestGeneration !== generation.current) return;
      if (result.version) {
        setCurrentVersion(result.version);
        derivedVersion.current = true;
      } else {
        throw new Error("No version returned by module");
      }
    } catch (err: unknown) {
      if (requestGeneration !== generation.current) return;
      const message = err instanceof Error ? err.message : "An unexpected error occurred during version search";
      setError(message);
    } finally {
      if (requestGeneration === generation.current) setIsSearching(false);
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

  const noModules = !modulesLoading && !modulesError && (!modules || modules.length === 0);
  const selectedModule = modules?.find((module) => module.id === Number(moduleId));

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {noModules && (
        <p className="text-sm text-amber-500">
          No modules available. Add a module before registering devices.
        </p>
      )}

      {modulesLoading && <p role="status">Loading sources…</p>}
      {modulesError && <p role="alert">Unable to load sources. Refresh to retry.</p>}
      {error && <p role="alert" className="text-sm text-destructive">{error}</p>}

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
        <Label htmlFor="device-module">Source</Label>
        <div className="flex gap-2">
          <div className="flex-1">
            <Select
              value={moduleId}
              onValueChange={(value) => { resetSearch(); setModuleId(value); }}
              disabled={noModules || modulesLoading || modulesError}
            >
              <SelectTrigger id="device-module">
                <SelectValue placeholder="Select a module" />
              </SelectTrigger>
              <SelectContent>
                {modules?.map((m) => (
                  <SelectItem key={m.id} value={m.id.toString()}>
                    {m.display_name || m.name} {m.status !== "active" ? "(automatic off)" : ""}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <SourceGuidance module={selectedModule} id="device-model-help" />
      </div>

      <div className="space-y-2">
        <Label htmlFor="device-model">Model</Label>
        <Input
          id="device-model"
          aria-describedby="device-model-help"
          value={model}
          onChange={(e) => { resetSearch(); setModel(e.target.value); }}
          placeholder="Enter source-specific model"
        />
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

      <div className="space-y-2">
        <Label htmlFor="device-version">Current Version</Label>
        <Input
          id="device-version"
          value={currentVersion}
          onChange={(e) => { generation.current++; derivedVersion.current = false; setIsSearching(false); setCurrentVersion(e.target.value); }}
          placeholder="e.g. 1.0.0"
        />
      </div>

      <div className="flex gap-2 pt-2">
        <Button type="submit" disabled={isPending || noModules || modulesLoading || modulesError}>
          {device ? "Save Changes" : "Add Device"}
        </Button>
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </form>
  );
}
