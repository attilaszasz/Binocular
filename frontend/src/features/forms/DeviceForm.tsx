import { useMemo } from "react";
import { useForm } from "react-hook-form";

import { ApiError, type DeviceType } from "../../api/types";
import { fieldLimits, maxLength, requiredTrimmed } from "./validation";

const LAST_DEVICE_TYPE_KEY = "binocular-last-device-type";

export interface DeviceFormValues {
  name: string;
  deviceTypeId: number;
  currentVersion: string;
  model: string;
  notes: string;
}

export interface DeviceFormSubmitValues {
  name: string;
  deviceTypeId: number;
  currentVersion: string;
  model?: string;
  notes: string;
}

interface DeviceFormProps {
  mode: "create" | "edit";
  deviceTypes: DeviceType[];
  initialValues?: DeviceFormValues;
  isSubmitting: boolean;
  onCancel: () => void;
  onSubmit: (values: DeviceFormSubmitValues) => Promise<void>;
}

function getInitialDeviceTypeId(deviceTypes: DeviceType[]): number {
  if (!deviceTypes.length) {
    return 0;
  }

  try {
    const stored = Number(localStorage.getItem(LAST_DEVICE_TYPE_KEY));
    if (deviceTypes.some((deviceType) => deviceType.id === stored)) {
      return stored;
    }
  } catch {
    // ignore
  }

  return deviceTypes[0].id;
}

export function DeviceForm({
  mode,
  deviceTypes,
  initialValues,
  isSubmitting,
  onCancel,
  onSubmit,
}: DeviceFormProps) {
  const defaultValues = useMemo<DeviceFormValues>(() => {
    if (initialValues) {
      return initialValues;
    }

    return {
      name: "",
      currentVersion: "",
      model: "",
      notes: "",
      deviceTypeId: getInitialDeviceTypeId(deviceTypes),
    };
  }, [initialValues, deviceTypes]);

  const {
    register,
    handleSubmit,
    reset,
    setError,
    clearErrors,
    formState: { errors, isDirty },
  } = useForm<DeviceFormValues>({
    defaultValues,
  });

  const submit = handleSubmit(async (values) => {
    clearErrors();

    try {
      const trimmedModel = values.model.trim();

      await onSubmit({
        name: values.name.trim(),
        currentVersion: values.currentVersion.trim(),
        model: trimmedModel.length > 0 ? trimmedModel : undefined,
        notes: values.notes.trim(),
        deviceTypeId: values.deviceTypeId,
      });

      if (mode === "create") {
        try {
          localStorage.setItem(LAST_DEVICE_TYPE_KEY, String(values.deviceTypeId));
        } catch {
          // ignore
        }
      }

      reset(defaultValues);
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.field === "name") {
          setError("name", { message: error.message });
          return;
        }
        if (error.field === "current_version") {
          setError("currentVersion", { message: error.message });
          return;
        }
        if (error.field === "model") {
          setError("model", { message: error.message });
          return;
        }
      }

      setError("root", {
        message: error instanceof Error ? error.message : "Request failed",
      });
    }
  });

  const noDeviceTypes = mode === "create" && !deviceTypes.length;

  return (
    <form className="space-y-4" onSubmit={submit}>
      <div>
        <label className="mb-1 block text-sm font-medium" htmlFor="device-name">
          Name
        </label>
        <input
          id="device-name"
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

      {mode === "create" ? (
        <div>
          <label className="mb-1 block text-sm font-medium" htmlFor="device-type-id">
            Device Type
          </label>
          <select
            id="device-type-id"
            {...register("deviceTypeId", {
              valueAsNumber: true,
              validate: (value) => (value > 0 ? true : "Select a device type"),
            })}
            className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:border-slate-700 dark:bg-slate-950"
          >
            {deviceTypes.map((deviceType) => (
              <option value={deviceType.id} key={deviceType.id}>
                {deviceType.name}
              </option>
            ))}
          </select>
          {noDeviceTypes ? (
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              No device types yet — create one first.
            </p>
          ) : null}
          {errors.deviceTypeId ? (
            <p className="mt-1 text-xs text-red-600">{errors.deviceTypeId.message}</p>
          ) : null}
        </div>
      ) : null}

      <div>
        <label className="mb-1 block text-sm font-medium" htmlFor="device-current-version">
          Current Version
        </label>
        <input
          id="device-current-version"
          type="text"
          {...register("currentVersion", {
            validate: {
              required: requiredTrimmed,
              maxLen: (value) => maxLength(value, fieldLimits.version),
            },
          })}
          className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:border-slate-700 dark:bg-slate-950"
        />
        {errors.currentVersion ? (
          <p className="mt-1 text-xs text-red-600">{errors.currentVersion.message}</p>
        ) : null}
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium" htmlFor="device-model">
          Model <span className="text-slate-500 dark:text-slate-400">(optional)</span>
        </label>
        <input
          id="device-model"
          type="text"
          {...register("model", {
            validate: {
              maxLen: (value) => maxLength(value, fieldLimits.model),
            },
          })}
          className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:border-slate-700 dark:bg-slate-950"
        />
        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
          Manufacturer&apos;s model identifier — e.g., ILCE-7M4
        </p>
        {errors.model ? <p className="mt-1 text-xs text-red-600">{errors.model.message}</p> : null}
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium" htmlFor="device-notes">
          Notes
        </label>
        <textarea
          id="device-notes"
          rows={3}
          {...register("notes", {
            validate: {
              maxLen: (value) => maxLength(value, fieldLimits.notes),
            },
          })}
          className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:border-slate-700 dark:bg-slate-950"
        />
        {errors.notes ? <p className="mt-1 text-xs text-red-600">{errors.notes.message}</p> : null}
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
          disabled={isSubmitting || noDeviceTypes}
          className="rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
        >
          {isSubmitting ? "Saving..." : mode === "create" ? "Add Device" : "Save Changes"}
        </button>
      </div>
    </form>
  );
}
