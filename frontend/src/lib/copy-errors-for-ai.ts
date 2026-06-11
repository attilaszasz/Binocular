/**
 * Formats module validation errors into structured markdown
 * suitable for pasting into an AI coding assistant.
 */

interface ValidationCheck {
  name: string;
  passed: boolean;
  message: string;
  line: number | null;
  fix_suggestion: string | null;
}

interface PhaseResult {
  phase: string;
  passed: boolean;
  checks: ValidationCheck[];
}

export interface ValidationError {
  valid?: boolean;
  phases?: PhaseResult[];
  detail?: string;
}

/**
 * Format validation errors as AI-friendly structured markdown.
 *
 * @param errors - The validation error object from the upload response.
 * @param filename - The filename of the uploaded module.
 * @returns Markdown-formatted error output.
 */
export function formatErrorsForAI(
  errors: ValidationError,
  filename: string = "uploaded_module.py"
): string {
  let md = `### Module Validation Failed\n`;
  md += `File: \`${filename}\`\n\n`;

  if (errors.phases) {
    errors.phases.forEach((phase) => {
      md += `#### Phase: ${phase.phase.toUpperCase()} (Passed: ${
        phase.passed ? "YES" : "NO"
      })\n`;
      phase.checks.forEach((check) => {
        if (!check.passed) {
          md += `- **Check**: \`${check.name}\`\n`;
          md += `  - **Message**: ${check.message}\n`;
          if (check.line !== null && check.line !== undefined) {
            md += `  - **Line**: ${check.line}\n`;
          }
          if (check.fix_suggestion) {
            md += `  - **Suggested Fix**: \`${check.fix_suggestion}\`\n`;
          }
        }
      });
      md += `\n`;
    });
  } else {
    md += `Error detail: ${errors.detail || "Unknown error"}\n`;
  }

  return md;
}

/**
 * Copy validation errors to clipboard in AI-friendly format.
 *
 * @param errors - The validation error object from the upload response.
 * @param filename - The filename of the uploaded module.
 * @returns Promise that resolves when the copy is complete.
 */
export async function copyErrorsForAI(
  errors: ValidationError,
  filename?: string
): Promise<void> {
  const text = formatErrorsForAI(errors, filename);
  await navigator.clipboard.writeText(text);
}
