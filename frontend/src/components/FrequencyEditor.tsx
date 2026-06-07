import { useCallback, useEffect, useMemo, useRef, useState, type KeyboardEvent } from 'react';

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
  const toggleRef = useRef<HTMLButtonElement>(null);

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
      className="space-y-3 rounded-xl border border-panel bg-surface p-3"
      onKeyDown={handleKeyDown}
      role="presentation"
    >
      {/* Preset segmented control */}
      <div role="radiogroup" aria-label="Check frequency interval" className="flex flex-wrap gap-1.5">
        {PRESETS.map((preset) => {
          const isSelected = selectedPreset === preset.value;
          return (
            <button
              key={preset.value}
              id={presetButtonId(preset.value)}
              ref={preset.value === '1h' ? firstPresetRef : undefined}
              type="button"
              role="radio"
              aria-checked={isSelected}
              tabIndex={isSelected ? 0 : -1}
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
              className={`rounded-lg px-3 py-1.5 text-xs font-semibold motion-safe:transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-focus/40 ${
                isSelected
                  ? 'bg-accent text-white'
                  : 'border border-muted bg-panel text-muted hover:border-muted-hover hover:text-ink-hover'
              }`}
            >
              {preset.label}
            </button>
          );
        })}
      </div>

      {/* Custom input */}
      {selectedPreset === 'custom' && (
        <div>
          <label htmlFor="freq-custom-input" className="block text-xs font-medium text-muted">
            Custom interval in minutes
          </label>
          <input
            id="freq-custom-input"
            type="number"
            min={1}
            max={10080}
            step={1}
            value={customMinutes}
            onChange={(e) => handleCustomChange(e.target.value)}
            aria-describedby={`${customHelpId}${customError !== null ? ` ${customErrorId}` : ''}`}
            className={`mt-1 h-9 w-full rounded-lg border bg-panel px-3 text-sm text-ink outline-none motion-safe:transition focus:ring-2 focus:ring-accent-focus/20 ${
              customError !== null ? 'border-error-border' : 'border-muted focus:border-accent'
            }`}
          />
          <p id={customHelpId} className="mt-1 text-xs text-muted">
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
      <div className="flex items-center justify-between border-t border-panel pt-2">
        <label htmlFor="freq-toggle" className="text-xs font-medium text-muted">
          Automatic checking
        </label>
        <button
          ref={toggleRef}
          id="freq-toggle"
          type="button"
          role="switch"
          aria-checked={isEnabled}
          aria-label={`Automatic checking: ${isEnabled ? 'on' : 'off'}`}
          onClick={() => setIsEnabled((prev) => !prev)}
          onKeyDown={(e) => {
            if (e.key === ' ') {
              e.preventDefault();
              setIsEnabled((prev) => !prev);
            }
          }}
          className={`relative inline-flex h-6 w-10 shrink-0 cursor-pointer items-center rounded-full motion-safe:transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-focus/40 ${
            isEnabled ? 'bg-accent' : 'bg-muted'
          }`}
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white shadow-sm motion-safe:transition-transform ${
              isEnabled ? 'translate-x-5' : 'translate-x-1'
            }`}
          />
        </button>
      </div>

      {/* Action buttons */}
      <div className="flex items-center justify-end gap-2 border-t border-panel pt-2">
        <button
          type="button"
          onClick={onCancel}
          className="rounded-lg border border-muted bg-panel px-3 py-1.5 text-xs font-medium text-muted hover:bg-panel-hover hover:text-ink-hover motion-safe:transition-colors"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={handleSave}
          disabled={selectedPreset === 'custom' && customError !== null}
          className="rounded-lg bg-accent px-3 py-1.5 text-xs font-medium text-white hover:bg-accent-hover motion-safe:transition-colors disabled:cursor-not-allowed disabled:opacity-60"
        >
          Save
        </button>
      </div>
    </div>
  );
}
