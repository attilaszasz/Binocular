import { type FormEvent } from 'react';
import { Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

export function ModuleUploadForm({
  selectedFile,
  onFileSelect,
  onUpload,
}: {
  selectedFile: File | null;
  onFileSelect: (file: File | null) => void;
  onUpload: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <form onSubmit={onUpload} className="flex flex-col gap-2 sm:flex-row sm:items-center">
      <label className="sr-only" htmlFor="moduleFile">
        Module file
      </label>
      <Input
        id="moduleFile"
        name="moduleFile"
        type="file"
        accept=".py,text/x-python"
        onChange={(event) => onFileSelect(event.currentTarget.files?.[0] ?? null)}
        className="sm:w-72"
      />
      {selectedFile !== null && (
        <span className="text-xs text-muted-foreground">{selectedFile.name}</span>
      )}
      <Button type="submit" variant="outline">
        <Plus size={16} className="mr-2" />
        Upload
      </Button>
    </form>
  );
}
