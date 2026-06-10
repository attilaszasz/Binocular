import { useCallback, useEffect, useMemo, useRef, useState, type KeyboardEvent } from 'react';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';

type PresetValue = '1h' | '6h' | '12h' | '24h' | 'custom';

const PRESETS: { value: PresetValue; minutes: number | null; label: string }[] = [
  { value: '1h', minutes: 60, label: '1h' },
  { value: '6h', minutes: 360, label: '6h' },
  { value: '12h', minutes: 720, label: '12h' },
  { value: '24h', minutes: 1440, label: '24h' },
  { value: 'custom', minutes: null, label: 'Custom' },
];

function resolvePreset(intervalMinutes: number | null): PresetValue {
  if (intervalMinutes === null) return '24h';
  const match = PRESETS.find((p) => p.minutes === intervalMinutes);
  return match?.value ?? 'custom';
}

export interface FrequencyEditorProps {
  currentIntervalMinutes: number | null;
  enabled: boolean;
  onSave: (payload: { enabled: boolean; intervalMinutes: number }) => void;
  onCancel: () => void;
  moduleId: number;
}

export function FrequencyEditor({
  currentIntervalMinutes,
  enabled,
  onSave,
  onCancel,
}: FrequencyEditorProps) {
  const initialPreset = resolvePreset(currentIntervalMinutes);
  const initialCustom = initialPreset === 'custom' ? (currentIntervalMinutes ?? 1440) : 1440;

  const [selectedPreset, setSelectedPreset] = useState<PresetValue>(initialPreset);
  const [customMinutes, setCustomMinutes] = useState<string>(String(initialCustom));
  const [isEnabled, setIsEnabled] = useState(enabled);
  const [customError, setCustomError] = useState<string | null>(null);

  const firstPresetRef = useRef<HTMLButtonElement>(null);

  const resolvedMinutes = useMemo(() => {
    if (selectedPreset === 'custom') {
      const parsed = parseInt(customMinutes, 10);
      if (Number.isNaN(parsed)) return null;
      return parsed;
    }
    const preset = PRESETS.find((p) => p.value === selectedPreset);
    return preset?.minutes ?? null;
  }, [selectedPreset, customMinutes]);

  const validateCustom = useCallback((value: string): string | null => {
    const trimmed = value.trim();
    if (trimmed === '') return null;
    const parsed = parseInt(trimmed, 10);
    if (!/^\d+$/.test(trimmed) || String(parsed) !== trimmed) {
      return 'Must be a whole number';
    }
    if (parsed < 1 || parsed > 10080) {
      return 'Must be between 1 and 10,080 minutes';
    }
    return null;
  }, []);

  const handleCustomChange = useCallback(
    (raw: string) => {
      setCustomMinutes(raw);
      const error = validateCustom(raw);
      setCustomError(error);
    },
    [validateCustom],
  );

  const handleSave = useCallback(() => {
    const minutes = resolvedMinutes;
    if (minutes === null) {
      setCustomError('Enter a valid number');
      return;
    }
    if (selectedPreset === 'custom' && customError !== null) return;
    onSave({ enabled: isEnabled, intervalMinutes: minutes });
  }, [resolvedMinutes, isEnabled, onSave, selectedPreset, customError]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onCancel();
      }
    },
    [onCancel],
  );

  useEffect(() => {
    firstPresetRef.current?.focus();
  }, []);

  const presetButtonId = (val: PresetValue) => `freq-preset-${val}`;
  const customErrorId = 'freq-custom-error';
  const customHelpId = 'freq-custom-help';

  return (
    <div
      className="space-y-3 rounded-xl border bg-background p-3"
      onKeyDown={handleKeyDown}
      role="presentation"
    >
      {/* Preset segmented control */}
      <div role="radiogroup" aria-label="Check frequency interval" className="flex flex-wrap gap-1.5">
        {PRESETS.map((preset) => {
          const isSelected = selectedPreset === preset.value;
          return (
            <Button
              key={preset.value}
              id={presetButtonId(preset.value)}
              ref={preset.value === '1h' ? firstPresetRef : undefined}
              type="button"
              role="radio"
              aria-checked={isSelected}
              tabIndex={isSelected ? 0 : -1}
              variant={isSelected ? 'default' : 'outline'}
              size="sm"
              className="text-xs font-semibold"
              onClick={() => setSelectedPreset(preset.value)}
              onKeyDown={(e) => {
                if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
                  e.preventDefault();
                  const idx = PRESETS.findIndex((p) => p.value === preset.value);
                  const next = PRESETS[(idx + 1) % PRESETS.length];
                  setSelectedPreset(next.value);
                  document.getElementById(presetButtonId(next.value))?.focus();
                }
                if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
                  e.preventDefault();
                  const idx = PRESETS.findIndex((p) => p.value === preset.value);
                  const prev = PRESETS[(idx - 1 + PRESETS.length) % PRESETS.length];
                  setSelectedPreset(prev.value);
                  document.getElementById(presetButtonId(prev.value))?.focus();
                }
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  handleSave();
                }
              }}
            >
              {preset.label}
            </Button>
          );
        })}
      </div>

      {/* Custom input */}
      {selectedPreset === 'custom' && (
        <div>
          <Label htmlFor="freq-custom-input" className="text-xs font-medium text-muted-foreground">
            Custom interval in minutes
          </Label>
          <input
            id="freq-custom-input"
            type="number"
            min={1}
            max={10080}
            step={1}
            value={customMinutes}
            onChange={(e) => handleCustomChange(e.target.value)}
            aria-describedby={`${customHelpId}${customError !== null ? ` ${customErrorId}` : ''}`}
            className={`mt-1 h-9 w-full rounded-lg border bg-card px-3 text-sm text-foreground outline-none transition focus:ring-2 focus:ring-ring/20 ${
              customError !== null ? 'border-destructive/30' : 'border focus:border-primary'
            }`}
          />
          <p id={customHelpId} className="mt-1 text-xs text-muted-foreground">
            {selectedPreset === 'custom' ? 'Enter a whole number between 1 and 10,080' : ''}
          </p>
          {customError !== null && (
            <p id={customErrorId} className="mt-1 text-xs text-red-600" role="alert">
              {customError}
            </p>
          )}
        </div>
      )}

      {/* Enabled toggle */}
      <div className="flex items-center justify-between border-t pt-2">
        <Label htmlFor="freq-toggle" className="text-xs font-medium text-muted-foreground">
          Automatic checking
        </Label>
        <Switch checked={isEnabled} onCheckedChange={setIsEnabled} id="freq-toggle" />
      </div>

      {/* Action buttons */}
      <div className="flex items-center justify-end gap-2 border-t pt-2">
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button
          type="button"
          onClick={handleSave}
          disabled={selectedPreset === 'custom' && customError !== null}
        >
          Save
        </Button>
      </div>
    </div>
  );
}
