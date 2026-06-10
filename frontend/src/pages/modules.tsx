import { useState } from "react";
import { Puzzle, Plus, Sparkles, Activity, Library } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useModules } from "@/hooks/use-modules";
import { ModuleCard } from "@/components/modules/ModuleCard";
import { ModuleUploadForm } from "@/components/modules/ModuleUploadForm";
import { StatCard } from "@/components/inventory/stat-card";

export function ModulesPage() {
  const { data: modules, isLoading, error } = useModules();
  const [showUpload, setShowUpload] = useState(false);

  const totalModules = modules?.length ?? 0;
  const officialModules = modules?.filter((m) => m.is_official).length ?? 0;
  const activeModules = modules?.filter((m) => m.status === "active").length ?? 0;

  if (error) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold tracking-tight">Modules</h1>
        <Card>
          <CardContent className="p-6">
            <p className="text-destructive">
              Failed to load modules. Please try again later.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
          <Puzzle className="h-8 w-8 text-primary" />
          Modules
        </h1>
        {!showUpload && (
          <Button onClick={() => setShowUpload(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Upload Module
          </Button>
        )}
      </div>

      {/* Stats row */}
      {!isLoading && totalModules > 0 && (
        <div className="grid gap-4 sm:grid-cols-3">
          <StatCard
            title="Total Modules"
            value={totalModules}
            icon={Library}
          />
          <StatCard
            title="Official Modules"
            value={officialModules}
            icon={Sparkles}
          />
          <StatCard
            title="Active Modules"
            value={activeModules}
            icon={Activity}
            description={`${activeModules} of ${totalModules} enabled`}
          />
        </div>
      )}

      {/* Upload Form Section */}
      {showUpload && (
        <Card className="border border-border bg-card text-card-foreground">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
            <div>
              <CardTitle>Upload Extension Module</CardTitle>
              <CardDescription>
                Upload a Python file conforming to the V1 firmware scraper contract.
              </CardDescription>
            </div>
            <Button variant="outline" size="sm" onClick={() => setShowUpload(false)}>
              Close
            </Button>
          </CardHeader>
          <CardContent>
            <ModuleUploadForm />
          </CardContent>
        </Card>
      )}

      {/* Loading states */}
      {isLoading && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="h-48 p-6 bg-muted/20" />
            </Card>
          ))}
        </div>
      )}

      {/* Empty states */}
      {!isLoading && totalModules === 0 && (
        <Card className="flex flex-col items-center justify-center p-12 text-center border border-border">
          <Puzzle className="h-12 w-12 text-muted-foreground/50 mb-4" />
          <h3 className="font-semibold text-lg">No modules loaded</h3>
          <p className="text-sm text-muted-foreground mt-2 max-w-sm">
            Extension modules provide the logic to scrape firmware websites.
            Upload your first module to get started.
          </p>
          {!showUpload && (
            <Button onClick={() => setShowUpload(true)} className="mt-4">
              <Plus className="mr-2 h-4 w-4" />
              Upload Module
            </Button>
          )}
        </Card>
      )}

      {/* Module Grid */}
      {!isLoading && totalModules > 0 && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {modules!.map((module) => (
            <ModuleCard key={module.id} module={module} />
          ))}
        </div>
      )}
    </div>
  );
}
