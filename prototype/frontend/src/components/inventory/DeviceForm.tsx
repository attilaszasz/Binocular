import { FormEvent } from 'react';

import { DeviceInput, InstalledModule, InventoryDevice } from '@/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

interface DeviceFormProps {
  formValues: DeviceInput;
  editingDevice: InventoryDevice | null;
  onFormChange: (field: keyof DeviceInput, value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onCancelEdit: () => void;
  onShowForm: (show: boolean) => void;
  showForm: boolean;
  modules: InstalledModule[];
}

export function DeviceForm({
  formValues,
  editingDevice,
  onFormChange,
  onSubmit,
  onCancelEdit,
  onShowForm,
  modules,
}: DeviceFormProps) {
  return (
    <form
      id="inventory-form"
      onSubmit={onSubmit}
      className="grid gap-3 rounded-2xl border bg-card p-4 shadow-sm md:grid-cols-5"
    >
      <div>
        <Label htmlFor="inventory-name" className="text-muted-foreground">
          Name
        </Label>
        <Input
          id="inventory-name"
          required
          value={formValues.name}
          onChange={(e) => onFormChange('name', e.target.value)}
          className="mt-1"
        />
      </div>

      <div>
        <Label htmlFor="inventory-model" className="text-muted-foreground">
          Model
        </Label>
        <Input
          id="inventory-model"
          required
          value={formValues.model}
          onChange={(e) => onFormChange('model', e.target.value)}
          className="mt-1"
        />
      </div>

      <div>
        <Label htmlFor="inventory-module" className="text-muted-foreground">
          Module
        </Label>
        {modules.length > 0 ? (
          <Select
            value={formValues.moduleId}
            onValueChange={(value) => onFormChange('moduleId', value)}
          >
            <SelectTrigger id="inventory-module" className="mt-1 w-full">
              <SelectValue placeholder="Select a module..." />
            </SelectTrigger>
            <SelectContent>
              {modules.map((module) => (
                <SelectItem key={module.moduleId} value={module.moduleId}>
                  {module.displayName}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        ) : (
          <>
            <Select disabled>
              <SelectTrigger
                id="inventory-module"
                className="mt-1 w-full cursor-not-allowed opacity-60"
              >
                <SelectValue placeholder="Select a module..." />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">Select a module...</SelectItem>
              </SelectContent>
            </Select>
            <p className="mt-1 text-xs text-muted-foreground">
              Install and validate a module first
            </p>
          </>
        )}
        {/* Hidden native select for test compatibility (shadcn Select uses portals unsupported by jsdom) */}
        <select
          data-testid="inventory-module-select"
          value={formValues.moduleId}
          onChange={(e) => onFormChange('moduleId', e.target.value)}
          className="sr-only"
          aria-hidden="true"
          tabIndex={-1}
        >
          <option value="">Select a module...</option>
          {modules.map((module) => (
            <option key={module.moduleId} value={module.moduleId}>
              {module.displayName}
            </option>
          ))}
        </select>
      </div>

      <div>
        <Label htmlFor="inventory-version" className="text-muted-foreground">
          Current version
        </Label>
        <Input
          id="inventory-version"
          required
          value={formValues.currentVersion}
          onChange={(e) => onFormChange('currentVersion', e.target.value)}
          className="mt-1"
        />
      </div>

      <div className="flex items-end gap-2">
        <Button type="submit" variant="default">
          {editingDevice === null ? 'Add' : 'Save'}
        </Button>
        {editingDevice !== null ? (
          <Button type="button" variant="outline" onClick={onCancelEdit}>
            Cancel
          </Button>
        ) : (
          <Button type="button" variant="outline" onClick={() => onShowForm(false)}>
            Cancel
          </Button>
        )}
      </div>
    </form>
  );
}
