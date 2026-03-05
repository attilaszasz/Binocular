import { useCallback, useRef, useState } from "react";
import { Upload } from "lucide-react";

interface ModuleUploadAreaProps {
  onUpload: (file: File, options?: { testUrl?: string; testModel?: string }) => void;
  isUploading: boolean;
  error: string | null;
}

export function ModuleUploadArea({ onUpload, isUploading, error }: ModuleUploadAreaProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [testUrl, setTestUrl] = useState("");
  const [testModel, setTestModel] = useState("");

  const handleFile = useCallback(
    (file: File) => {
      const options: { testUrl?: string; testModel?: string } = {};
      if (testUrl.trim()) options.testUrl = testUrl.trim();
      if (testModel.trim()) options.testModel = testModel.trim();
      onUpload(file, Object.keys(options).length > 0 ? options : undefined);
    },
    [onUpload, testUrl, testModel],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) {
        handleFile(file);
      }
    },
    [handleFile],
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragOver(false);
  }, []);

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) {
        handleFile(file);
      }
      // Reset input so re-selecting same file works
      e.target.value = "";
    },
    [handleFile],
  );

  return (
    <div className="space-y-2">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div>
          <label htmlFor="test-url" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
            Test URL <span className="text-slate-400">(optional)</span>
          </label>
          <input
            id="test-url"
            type="url"
            placeholder="https://example.com/firmware"
            value={testUrl}
            onChange={(e) => setTestUrl(e.target.value)}
            disabled={isUploading}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm placeholder:text-slate-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
          />
        </div>
        <div>
          <label htmlFor="test-model" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
            Device Model <span className="text-slate-400">(optional)</span>
          </label>
          <input
            id="test-model"
            type="text"
            placeholder="TEST-001"
            value={testModel}
            onChange={(e) => setTestModel(e.target.value)}
            disabled={isUploading}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm placeholder:text-slate-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
          />
        </div>
      </div>
      <div
        data-testid="upload-dropzone"
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-6 transition-colors ${
          isDragOver
            ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
            : "border-slate-300 hover:border-slate-400 dark:border-slate-700 dark:hover:border-slate-600"
        }`}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            inputRef.current?.click();
          }
        }}
        role="button"
        tabIndex={0}
        aria-label="Upload module file"
      >
        <Upload className="mb-2 h-8 w-8 text-slate-400" />
        <p className="text-sm text-slate-600 dark:text-slate-300">
          {isUploading ? "Uploading…" : "Drop a .py module file here or click to browse"}
        </p>
        <input
          ref={inputRef}
          type="file"
          accept=".py"
          onChange={handleChange}
          disabled={isUploading}
          className="hidden"
          aria-label="Select module file"
        />
      </div>

      {error && (
        <div
          role="alert"
          className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-900 dark:bg-red-900/20 dark:text-red-300"
        >
          {error}
        </div>
      )}
    </div>
  );
}
