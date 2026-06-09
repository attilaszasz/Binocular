import { useState, useCallback, useEffect } from 'react';
import { BookOpen, ChevronDown, ChevronUp, Download, Package, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';

const KIT_FILES = [
  {
    filename: 'AI_INSTRUCTIONS.md',
    label: 'AI Instructions',
    description: 'Give this file to your AI tool',
  },
  {
    filename: 'STARTER_TEMPLATE.py',
    label: 'Starter Template',
    description: 'Minimal module to customize',
  },
  {
    filename: 'EXAMPLE_MODULE.py',
    label: 'Example Module',
    description: 'Working reference implementation',
  },
  {
    filename: 'CONTRACT_REFERENCE.md',
    label: 'Contract Reference',
    description: 'Full authoring contract docs',
  },
] as const;

const SESSION_KEY = 'binocular:module-guidance-collapsed';

export function ModuleGuidanceSection() {
  const [isCollapsed, setIsCollapsed] = useState(() => {
    try {
      return sessionStorage.getItem(SESSION_KEY) === '1';
    } catch {
      return false;
    }
  });

  const toggleCollapsed = useCallback(() => {
    setIsCollapsed((prev) => {
      const next = !prev;
      try {
        if (next) {
          sessionStorage.setItem(SESSION_KEY, '1');
        } else {
          sessionStorage.removeItem(SESSION_KEY);
        }
      } catch {
        // sessionStorage unavailable
      }
      return next;
    });
  }, []);

  // Sync collapsed state on mount (handles multi-tab)
  useEffect(() => {
    const handleStorage = (e: StorageEvent) => {
      if (e.key === SESSION_KEY) {
        setIsCollapsed(e.newValue === '1');
      }
    };
    window.addEventListener('storage', handleStorage);
    return () => window.removeEventListener('storage', handleStorage);
  }, []);

  return (
    <div className="rounded-2xl border bg-card p-4 shadow-sm">
      <button
        type="button"
        onClick={toggleCollapsed}
        className="flex w-full items-center justify-between text-left"
      >
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
            <Sparkles size={20} className="text-primary" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-foreground">
              Create a Module with AI
            </h3>
            {isCollapsed && (
              <p className="text-xs text-muted-foreground">
                Download the AI Module Kit to get started
              </p>
            )}
          </div>
        </div>
        {isCollapsed ? (
          <ChevronDown size={16} className="text-muted-foreground" />
        ) : (
          <ChevronUp size={16} className="text-muted-foreground" />
        )}
      </button>

      {!isCollapsed && (
        <div className="mt-4 space-y-4">
          <p className="text-sm text-muted-foreground">
            Extension modules are Python scripts that scrape manufacturer support pages
            to check for firmware updates. You can create one using any AI coding tool
            (ChatGPT, Claude, Cursor, etc.) by following these steps:
          </p>

          <div className="grid gap-3 sm:grid-cols-3">
            <StepCard
              step={1}
              icon={<Download size={16} />}
              title="Download the Kit"
              description="Get the AI Instructions file or the full kit bundle below"
            />
            <StepCard
              step={2}
              icon={<Sparkles size={16} />}
              title="Give to Your AI Tool"
              description="Paste the AI Instructions file into your AI coding assistant"
            />
            <StepCard
              step={3}
              icon={<Package size={16} />}
              title="Upload the Module"
              description="Upload the generated .py file using the form above"
            />
          </div>

          <div className="rounded-xl bg-background p-3">
            <div className="mb-2 flex items-center gap-2">
              <BookOpen size={14} className="text-muted-foreground" />
              <span className="text-xs font-medium text-foreground">
                AI Module Kit — Download Files
              </span>
            </div>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
              {KIT_FILES.map((file) => (
                <a
                  key={file.filename}
                  href={`/api/v1/module-kit/files/${file.filename}`}
                  download={file.filename}
                  className="group flex items-center gap-2 rounded-lg border border-transparent px-2 py-1.5 text-sm transition-colors hover:border-border hover:bg-accent"
                >
                  <Download
                    size={12}
                    className="shrink-0 text-muted-foreground group-hover:text-foreground"
                  />
                  <div className="min-w-0">
                    <div className="truncate text-xs font-medium text-foreground">
                      {file.label}
                    </div>
                    <div className="truncate text-[11px] text-muted-foreground">
                      {file.description}
                    </div>
                  </div>
                </a>
              ))}
            </div>
            <div className="mt-2 border-t pt-2">
              <Button
                variant="outline"
                size="sm"
                className="w-full sm:w-auto"
                asChild
              >
                <a href="/api/v1/module-kit/bundle" download="binocular-module-kit.zip">
                  <Download size={14} className="mr-2" />
                  Download Full Kit (.zip)
                </a>
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function StepCard({
  step,
  icon,
  title,
  description,
}: {
  step: number;
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="flex items-start gap-3 rounded-xl bg-background p-3">
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-xs font-semibold text-primary">
        {step}
      </div>
      <div className="min-w-0">
        <div className="flex items-center gap-1.5">
          <span className="text-muted-foreground">{icon}</span>
          <span className="text-xs font-medium text-foreground">{title}</span>
        </div>
        <p className="mt-0.5 text-[11px] leading-snug text-muted-foreground">
          {description}
        </p>
      </div>
    </div>
  );
}
