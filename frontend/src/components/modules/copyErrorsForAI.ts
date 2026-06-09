import type { ModuleValidationSummary } from '@/api';

/**
 * Format validation errors into a structured text block optimized for AI coding tools.
 * Includes an instruction preamble, error codes, messages, and phase context.
 */
export function formatErrorsForAI(summary: ModuleValidationSummary): string {
  const lines: string[] = [];

  lines.push(
    '## Binocular Module Validation Errors',
    '',
    'The following validation errors occurred when uploading a Binocular extension module.',
    'Please fix these errors in the Python module file so it passes validation.',
    '',
  );

  for (const phase of [summary.static_phase, summary.runtime_phase]) {
    if (phase.findings.length === 0) continue;

    lines.push(`### ${capitalize(phase.phase)} Phase — ${phase.status.toUpperCase()}`);
    lines.push('');

    for (const finding of phase.findings) {
      lines.push(`- **${finding.code}**: ${finding.message}`);
    }

    if (phase.message) {
      lines.push('', `> ${phase.message}`);
    }

    lines.push('');
  }

  lines.push(
    '### Module Contract Summary',
    '',
    '- The module must have a `MODULE_METADATA` dict with `module_id` (non-empty str) and `display_name` (non-empty str).',
    '- The module must define `async def check_firmware(input: ModuleCheckInput, scrape_client: ScrapeClient)`.',
    '- All HTTP requests must use `scrape_client.fetch()`, not raw HTTP libraries.',
    '- Import types from `binocular.extensions.contract` and `binocular.scraping.client`.',
  );

  return lines.join('\n');
}

/**
 * Copy formatted validation errors to the clipboard.
 * Returns true on success, false on failure.
 */
export async function copyErrorsToClipboard(
  summary: ModuleValidationSummary,
): Promise<boolean> {
  const text = formatErrorsForAI(summary);

  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}

/**
 * Check if the validation summary has any findings worth copying.
 */
export function hasFindings(summary: ModuleValidationSummary): boolean {
  return (
    summary.static_phase.findings.length > 0 ||
    summary.runtime_phase.findings.length > 0
  );
}

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}
