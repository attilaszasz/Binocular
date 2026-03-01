export const fieldLimits = {
  name: 200,
  version: 100,
  url: 2048,
  notes: 2000,
};

export function requiredTrimmed(value: string): true | string {
  if (!value || !value.trim()) {
    return "This field is required";
  }
  return true;
}

export function maxLength(value: string, limit: number): true | string {
  if (value.length > limit) {
    return `Must be ${limit} characters or fewer`;
  }
  return true;
}

export function validHttpUrl(value: string): true | string {
  try {
    const parsed = new URL(value);
    if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
      return "URL must start with http:// or https://";
    }
    return true;
  } catch {
    return "Enter a valid URL";
  }
}
