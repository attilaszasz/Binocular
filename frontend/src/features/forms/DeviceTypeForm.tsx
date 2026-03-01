import { useMemo } from "react";
import { useForm } from "react-hook-form";

import { ApiError } from "../../api/types";
import { fieldLimits, maxLength, requiredTrimmed, validHttpUrl } from "./validation";

export interface DeviceTypeFormValues {
  name: string;
  firmwareSourceUrl: string;
  checkFrequencyMinutes: number;
}

interface DeviceTypeFormProps {
  mode: "create" | "edit";
  initialValues?: DeviceTypeFormValues;
  isSubmitting: boolean;
  onCancel: () => void;
  onSubmit: (values: DeviceTypeFormValues) => Promise<void>;
}

export function DeviceTypeForm({
  mode,
  initialValues,
  isSubmitting,
  onCancel,
  onSubmit,
}: DeviceTypeFormProps) {
  const defaultValues = useMemo<DeviceTypeFormValues>(() => {
    if (initialValues) {
      return initialValues;
    }

    return {
      name: "",
      firmwareSourceUrl: "",
      checkFrequencyMinutes: 360,
    };
  }, [initialValues]);

  const {
    register,
    handleSubmit,
    reset,
    setError,
    clearErrors,
    formState: { errors, isDirty },
  } = useForm<DeviceTypeFormValues>({
    defaultValues,
  });

  const submit = handleSubmit(async (values) => {
    clearErrors();

    try {
      await onSubmit({
        name: values.name.trim(),
        firmwareSourceUrl: values.firmwareSourceUrl.trim(),
        checkFrequencyMinutes: values.checkFrequencyMinutes,
      });
      reset(defaultValues);
    } catch (error) {
      if (error instanceof ApiError && error.field === "name") {
        setError("name", { message: error.message });
        return;
      }

      if (error instanceof ApiError && error.field === "firmware_source_url") {
        setError("firmwareSourceUrl", { message: error.message });
        return;
      }

      setError("root", {
        message: error instanceof Error ? error.message : "Request failed",
      });
    }
  });

  return (
    <form className="space-y-4" onSubmit={submit}>
      <div>
        <label className="mb-1 block text-sm font-medium" htmlFor="module-name">
          Name
        </label>
        <input
          id="module-name"
          type="text"
          {...register("name", {
            validate: {
              required: requiredTrimmed,
              maxLen: (value) => maxLength(value, fieldLimits.name),
            },
          })}
          className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:border-slate-700 dark:bg-slate-950"
        />
        {errors.name ? <p className="mt-1 text-xs text-red-600">{errors.name.message}</p> : null}
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium" htmlFor="module-firmware-url">
          Firmware Source URL
        </label>
        <input
          id="module-firmware-url"
          type="url"
          {...register("firmwareSourceUrl", {
            validate: {
              required: requiredTrimmed,
              maxLen: (value) => maxLength(value, fieldLimits.url),
              url: validHttpUrl,
            },
          })}
          className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:border-slate-700 dark:bg-slate-950"
        />
        {errors.firmwareSourceUrl ? (
          <p className="mt-1 text-xs text-red-600">{errors.firmwareSourceUrl.message}</p>
        ) : null}
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium" htmlFor="module-check-frequency">
          Check Frequency (minutes)
        </label>
        <input
          id="module-check-frequency"
          type="number"
          min={1}
          {...register("checkFrequencyMinutes", {
            valueAsNumber: true,
            validate: (value) =>
              Number.isFinite(value) && value >= 1 ? true : "Must be 1 or greater",
          })}
          className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:border-slate-700 dark:bg-slate-950"
        />
        {errors.checkFrequencyMinutes ? (
          <p className="mt-1 text-xs text-red-600">{errors.checkFrequencyMinutes.message}</p>
        ) : null}
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium" htmlFor="module-extension-id">
          Extension Module File
        </label>
        <input
          id="module-extension-id"
          type="text"
          value="Coming in a future release"
          readOnly
          disabled
          className="w-full cursor-not-allowed rounded-md border border-slate-300 bg-slate-100 px-3 py-2 text-sm text-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400"
        />
      </div>

      {errors.root ? <p className="text-xs text-red-600">{errors.root.message}</p> : null}

      <div className="flex items-center justify-end gap-2">
        <button
          type="button"
          onClick={() => {
            if (isDirty && !window.confirm("Discard unsaved changes?")) {
              return;
            }
            onCancel();
          }}
          className="rounded-md border border-slate-300 px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:border-slate-700"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={isSubmitting}
          className="rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
        >
          {isSubmitting ? "Saving..." : mode === "create" ? "Add Module" : "Save Changes"}
        </button>
      </div>
    </form>
  );
}
