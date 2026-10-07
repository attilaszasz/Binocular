/** Only absolute HTTP(S) links without credentials/control characters act. */
export function safeSourceUrl(value?: string): string | undefined {
  if (!value || [...value].some(c => c.charCodeAt(0) < 33 || c.charCodeAt(0) === 127) || /\s/u.test(value)) return undefined;
  if (!/^https?:\/\//i.test(value)) return undefined;
  try {
    const url = new URL(value);
    if (!url.hostname || url.username || url.password) return undefined;
    return value;
  } catch {
    return undefined;
  }
}
