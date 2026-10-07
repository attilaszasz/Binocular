import type { Module } from "@/lib/api";
import { safeSourceUrl } from "@/lib/source-guidance";

export function SourceGuidance({ module, id }: { module?: Module; id: string }) {
  const help = safeSourceUrl(module?.help_url);
  const canonical = safeSourceUrl(module?.source_url);
  return <div id={id} className="space-y-2 text-sm break-words">
    {module ? <>
      <p>{module.coverage_notes || `Source type: ${module.device_type}`}</p>
      {!!module.model_examples?.length && <p>Model examples: {module.model_examples.join("; ")}. Enter a model as free text.</p>}
      {help && <a className="block underline" href={help} target="_blank" rel="noopener noreferrer">Model naming and source help</a>}
      {canonical && <a className="block underline" href={canonical} target="_blank" rel="noopener noreferrer">View module source page (scrape endpoint)</a>}
      {module.status !== "active" && <p role="status">Automatic monitoring is off for this source. Manual single, bulk checks and version search remain available without resuming.</p>}
    </> : <p>Select a source for model naming help.</p>}
  </div>;
}
