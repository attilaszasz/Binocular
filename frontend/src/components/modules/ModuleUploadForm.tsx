import React, { useState, useRef } from "react";
import {
  Upload,
  FileCode,
  CheckCircle2,
  XCircle,
  Copy,
  AlertTriangle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { useUploadModule } from "@/hooks/use-modules";
import { ApiError } from "@/lib/api";

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

interface ValidationError {
  valid?: boolean;
  phases?: PhaseResult[];
  detail?: string;
}

export function ModuleUploadForm() {
  const uploadMutation = useUploadModule();
  const [file, setFile] = useState<File | null>(null);
  const [runPhase2, setRunPhase2] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const [copied, setCopied] = useState(false);
  const [validationErrors, setValidationErrors] = useState<ValidationError | null>(
    null
  );
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && droppedFile.name.endsWith(".py")) {
      setFile(droppedFile);
      setValidationErrors(null);
    } else {
      alert("Please upload a Python (.py) file.");
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      if (selectedFile.name.endsWith(".py")) {
        setFile(selectedFile);
        setValidationErrors(null);
      } else {
        alert("Please select a Python (.py) file.");
      }
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setValidationErrors(null);
    uploadMutation.mutate(
      { file, runPhase2 },
      {
        onSuccess: () => {
          setFile(null);
          if (fileInputRef.current) {
            fileInputRef.current.value = "";
          }
        },
        onError: (err: unknown) => {
          if (
            err instanceof ApiError &&
            err.body &&
            typeof err.body === "object" &&
            "validation_result" in err.body
          ) {
            const body = err.body as { validation_result: ValidationError };
            setValidationErrors(body.validation_result);
          } else {
            const error = err as Error;
            setValidationErrors({
              detail: error.message || "Failed to upload module",
            });
          }
        },
      }
    );
  };

  const formatErrorsForAI = () => {
    if (!validationErrors) return "";

    let md = `### Module Validation Failed\n`;
    md += `File: \`${file?.name || "uploaded_module.py"}\`\n\n`;

    if (validationErrors.phases) {
      validationErrors.phases.forEach((phase) => {
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
      md += `Error detail: ${validationErrors.detail || "Unknown error"}\n`;
    }

    return md;
  };

  const handleCopyForAI = () => {
    const text = formatErrorsForAI();
    if (text) {
      navigator.clipboard.writeText(text).then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      });
    }
  };

  return (
    <div className="space-y-6">
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Warning Banner */}
        <div className="flex items-start gap-3 rounded-lg border border-yellow-500/20 bg-yellow-500/5 p-4 text-sm text-yellow-600 dark:text-yellow-400">
          <AlertTriangle className="h-5 w-5 shrink-0 mt-0.5" />
          <div>
            <h4 className="font-semibold">Trust Boundary Warning</h4>
            <p className="mt-1 text-xs opacity-90 leading-normal">
              Uploaded modules execute in-process with the full privileges of the
              application. Only upload modules from trusted sources that you have
              personally reviewed.
            </p>
          </div>
        </div>

        {/* Drag and Drop zone */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`flex flex-col items-center justify-center border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
            isDragOver
              ? "border-primary bg-primary/5"
              : "border-border hover:border-primary/50 hover:bg-accent/10"
          }`}
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept=".py"
            className="hidden"
          />
          {file ? (
            <div className="flex flex-col items-center space-y-2">
              <FileCode className="h-10 w-10 text-primary" />
              <span className="font-medium text-sm text-foreground">
                {file.name}
              </span>
              <span className="text-xs text-muted-foreground">
                {(file.size / 1024).toFixed(2)} KB
              </span>
            </div>
          ) : (
            <div className="flex flex-col items-center space-y-2 text-muted-foreground">
              <Upload className="h-10 w-10 text-muted-foreground/60" />
              <span className="font-medium text-sm text-foreground">
                Click or drag & drop Python module file here
              </span>
              <span className="text-xs">Only .py extension files are supported</span>
            </div>
          )}
        </div>

        {/* Settings options */}
        <div className="flex items-center space-x-3 bg-card p-3 rounded-lg border border-border/80">
          <Switch
            id="run-phase2"
            checked={runPhase2}
            onCheckedChange={setRunPhase2}
          />
          <div className="space-y-0.5">
            <Label htmlFor="run-phase2" className="text-sm font-medium">
              Run Phase 2 (Runtime Verification)
            </Label>
            <p className="text-xs text-muted-foreground leading-normal">
              Executes the module's check_firmware function with mock arguments
              on load.
            </p>
          </div>
        </div>

        {/* Buttons */}
        <div className="flex gap-2 justify-end">
          {file && (
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setFile(null);
                setValidationErrors(null);
              }}
            >
              Clear
            </Button>
          )}
          <Button
            type="submit"
            disabled={!file || uploadMutation.isPending}
            className="px-6"
          >
            {uploadMutation.isPending ? "Validating & Uploading..." : "Upload Module"}
          </Button>
        </div>
      </form>

      {/* Validation success / failures */}
      {uploadMutation.isSuccess && (
        <div className="flex items-start gap-3 rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-4 text-emerald-600 dark:text-emerald-400">
          <CheckCircle2 className="h-5 w-5 shrink-0 mt-0.5" />
          <div>
            <h4 className="font-semibold text-sm">Module Uploaded Successfully</h4>
            <p className="text-xs mt-1">
              Your module is registered and ready to use in the device inventory.
            </p>
          </div>
        </div>
      )}

      {validationErrors && (
        <div className="rounded-lg border border-destructive/20 bg-destructive/5 p-4 space-y-4">
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-3 text-destructive">
              <XCircle className="h-5 w-5 shrink-0 mt-0.5" />
              <div>
                <h4 className="font-semibold text-sm">Module Validation Failed</h4>
                <p className="text-xs mt-1">
                  The uploaded file does not comply with the extension module
                  contract.
                </p>
              </div>
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleCopyForAI}
              className="flex items-center gap-1.5 text-xs h-7 border border-border"
            >
              <Copy className="h-3.5 w-3.5" />
              {copied ? "Copied!" : "Copy for AI"}
            </Button>
          </div>

          {validationErrors.phases ? (
            <div className="space-y-4 pt-2 border-t border-border/40">
              {validationErrors.phases.map((phase, pIdx) => {
                const failedChecks = phase.checks.filter((c) => !c.passed);
                if (failedChecks.length === 0) return null;

                return (
                  <div key={pIdx} className="space-y-2">
                    <h5 className="text-xs font-semibold uppercase text-muted-foreground tracking-wider">
                      Phase: {phase.phase}
                    </h5>
                    <div className="space-y-2 pl-3 border-l-2 border-destructive/40">
                      {failedChecks.map((check, cIdx) => (
                        <div key={cIdx} className="space-y-1 text-xs">
                          <div className="font-semibold text-foreground flex items-center gap-2">
                            <span>Check: {check.name}</span>
                            {check.line !== null && check.line !== undefined && (
                              <span className="text-[10px] bg-muted px-1.5 py-0.5 rounded font-mono text-muted-foreground">
                                Line {check.line}
                              </span>
                            )}
                          </div>
                          <p className="text-muted-foreground leading-normal">
                            {check.message}
                          </p>
                          {check.fix_suggestion && (
                            <div className="bg-muted/50 p-2 rounded font-mono text-[10px] text-foreground mt-1 border border-border/40">
                              <span className="text-muted-foreground block text-[9px] uppercase font-sans font-semibold tracking-wide mb-1">
                                Suggested Fix
                              </span>
                              {check.fix_suggestion}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-xs text-destructive pl-8 leading-normal">
              {validationErrors.detail}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
