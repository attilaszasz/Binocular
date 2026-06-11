import { useState, useEffect } from "react";
import {
  BookOpen,
  Download,
  ChevronDown,
  ChevronUp,
  FileCode,
  Bot,
  TestTube,
  Upload,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface KitFile {
  name: string;
  description: string;
  size_bytes: number;
  url: string;
}

interface KitListResponse {
  files: KitFile[];
}

export function ModuleGuidanceSection() {
  const [isExpanded, setIsExpanded] = useState(true);
  const [kitFiles, setKitFiles] = useState<KitFile[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetch("/api/v1/module-kit/")
      .then((r) => r.json())
      .then((data: KitListResponse) => {
        setKitFiles(data.files || []);
      })
      .catch(() => {
        setKitFiles([]);
      })
      .finally(() => setIsLoading(false));
  }, []);

  const downloadFile = (file: KitFile) => {
    const link = document.createElement("a");
    link.href = file.url;
    link.download = file.name;
    link.click();
  };

  const downloadAllAsZip = async () => {
    // Download files individually for now — client-side ZIP requires JSZip.
    // Each file triggers a separate download.
    for (const file of kitFiles) {
      downloadFile(file);
      // Small delay between downloads to avoid browser blocking.
      await new Promise((resolve) => setTimeout(resolve, 200));
    }
  };

  const formatSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    return `${(bytes / 1024).toFixed(1)} KB`;
  };

  const getFileIcon = (name: string) => {
    if (name.endsWith(".py")) return FileCode;
    if (name.includes("AI_INSTRUCTIONS")) return Bot;
    return BookOpen;
  };

  return (
    <Card className="border border-border bg-card text-card-foreground">
      <CardHeader
        className="flex flex-row items-center justify-between space-y-0 pb-2 cursor-pointer select-none"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-2">
          <BookOpen className="h-5 w-5 text-primary" />
          <div>
            <CardTitle className="text-base">Create a Module</CardTitle>
            <CardDescription className="text-xs mt-0.5">
              Step-by-step guide to building your own firmware detection module
            </CardDescription>
          </div>
        </div>
        <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
          {isExpanded ? (
            <ChevronUp className="h-4 w-4" />
          ) : (
            <ChevronDown className="h-4 w-4" />
          )}
        </Button>
      </CardHeader>

      {isExpanded && (
        <CardContent className="space-y-5 pt-2">
          {/* Steps */}
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {[
              {
                step: 1,
                icon: Download,
                title: "Get the Kit",
                description: "Download the AI Module Kit or read the contract reference",
              },
              {
                step: 2,
                icon: FileCode,
                title: "Write Your Module",
                description: "Use the starter template and example as a guide",
              },
              {
                step: 3,
                icon: TestTube,
                title: "Test Locally",
                description: "Run the test harness to validate contract compliance",
              },
              {
                step: 4,
                icon: Upload,
                title: "Upload",
                description: "Upload your module via the form above",
              },
            ].map((item) => (
              <div
                key={item.step}
                className="flex gap-3 p-3 rounded-lg border border-border/60 bg-muted/20"
              >
                <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary text-xs font-bold">
                  {item.step}
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-1.5">
                    <item.icon className="h-3.5 w-3.5 text-muted-foreground" />
                    <span className="text-sm font-medium">{item.title}</span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-0.5 leading-normal">
                    {item.description}
                  </p>
                </div>
              </div>
            ))}
          </div>

          {/* Contract Quick Reference */}
          <div className="rounded-lg border border-border/60 bg-muted/10 p-4">
            <h4 className="text-sm font-semibold mb-2">V1 Contract Requirements</h4>
            <div className="grid gap-1.5 text-xs text-muted-foreground">
              <div className="flex items-start gap-2">
                <code className="bg-muted px-1.5 py-0.5 rounded text-[10px] font-mono text-foreground shrink-0">
                  MODULE_VERSION
                </code>
                <span>String constant, e.g. &quot;1.0.0&quot;</span>
              </div>
              <div className="flex items-start gap-2">
                <code className="bg-muted px-1.5 py-0.5 rounded text-[10px] font-mono text-foreground shrink-0">
                  SUPPORTED_DEVICE_TYPE
                </code>
                <span>String constant, e.g. &quot;camera&quot;, &quot;lens&quot;, &quot;flash&quot;</span>
              </div>
              <div className="flex items-start gap-2">
                <code className="bg-muted px-1.5 py-0.5 rounded text-[10px] font-mono text-foreground shrink-0">
                  check_firmware()
                </code>
                <span>
                  Function with 3 params (url, model, http_client) → returns dict with
                  &quot;latest_version&quot;
                </span>
              </div>
            </div>
          </div>

          {/* Kit Files */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-semibold">AI Module Kit</h4>
              {kitFiles.length > 0 && (
                <Button
                  variant="default"
                  size="sm"
                  className="h-7 text-xs"
                  onClick={downloadAllAsZip}
                >
                  <Download className="mr-1.5 h-3.5 w-3.5" />
                  Download All
                </Button>
              )}
            </div>

            {isLoading ? (
              <div className="grid gap-2 sm:grid-cols-2">
                {[1, 2, 3, 4].map((i) => (
                  <div
                    key={i}
                    className="h-16 rounded-lg border border-border/40 bg-muted/20 animate-pulse"
                  />
                ))}
              </div>
            ) : kitFiles.length > 0 ? (
              <div className="grid gap-2 sm:grid-cols-2">
                {kitFiles.map((file) => {
                  const Icon = getFileIcon(file.name);
                  return (
                    <button
                      key={file.name}
                      type="button"
                      onClick={() => downloadFile(file)}
                      className="flex items-start gap-3 p-3 rounded-lg border border-border/60 hover:border-primary/40 hover:bg-accent/10 transition-colors text-left group"
                    >
                      <Icon className="h-4 w-4 text-muted-foreground mt-0.5 group-hover:text-primary transition-colors" />
                      <div className="min-w-0 flex-1">
                        <div className="text-sm font-medium truncate group-hover:text-primary transition-colors">
                          {file.name}
                        </div>
                        <p className="text-xs text-muted-foreground leading-normal mt-0.5">
                          {file.description}
                        </p>
                        <span className="text-[10px] text-muted-foreground/60 mt-0.5 block">
                          {formatSize(file.size_bytes)}
                        </span>
                      </div>
                      <Download className="h-3.5 w-3.5 text-muted-foreground/40 mt-0.5 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </button>
                  );
                })}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">
                Kit files are not available. The backend may not be running.
              </p>
            )}
          </div>
        </CardContent>
      )}
    </Card>
  );
}
