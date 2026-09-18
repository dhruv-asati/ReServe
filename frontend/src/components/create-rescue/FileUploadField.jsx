import { useId, useRef, useState } from 'react';
import { UploadCloud, X, FileText, Image as ImageIcon } from 'lucide-react';
import { cn } from '@/utils/cn';

const DEFAULT_MAX_SIZE_MB = 10;

function formatBytes(bytes) {
  if (!Number.isFinite(bytes)) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * FileUploadField — frontend-only upload dropzone, reused for the Food
 * "image upload" and Medical "supporting document upload" sections.
 *
 * No network call is ever made: selected files are held as in-memory File
 * objects for preview only (see CreateRescue.jsx, which strips them down to
 * plain {name, size, type} metadata before anything is persisted to
 * localStorage). `preview="thumbnail"` renders an image grid; `preview="list"`
 * renders a document row list with a file-type icon.
 */
export default function FileUploadField({
  label,
  hint,
  error,
  required = false,
  accept,
  multiple = true,
  maxSizeMb = DEFAULT_MAX_SIZE_MB,
  preview = 'list',
  files = [],
  onFilesChange,
  emptyLabel = 'Click to upload or drag and drop',
}) {
  const generatedId = useId();
  const inputId = generatedId;
  const inputRef = useRef(null);
  const [dragActive, setDragActive] = useState(false);

  function addFiles(fileList) {
    const incoming = Array.from(fileList).filter(
      (file) => file.size <= maxSizeMb * 1024 * 1024,
    );
    if (incoming.length === 0) return;

    const withPreviews = incoming.map((file) => ({
      file,
      id: `${file.name}-${file.size}-${file.lastModified}`,
      previewUrl: preview === 'thumbnail' ? URL.createObjectURL(file) : null,
    }));

    onFilesChange(multiple ? [...files, ...withPreviews] : withPreviews);
  }

  function handleInputChange(event) {
    if (event.target.files?.length) addFiles(event.target.files);
    event.target.value = '';
  }

  function handleDrop(event) {
    event.preventDefault();
    setDragActive(false);
    if (event.dataTransfer.files?.length) addFiles(event.dataTransfer.files);
  }

  function removeFile(id) {
    const target = files.find((f) => f.id === id);
    if (target?.previewUrl) URL.revokeObjectURL(target.previewUrl);
    onFilesChange(files.filter((f) => f.id !== id));
  }

  return (
    <div className="w-full">
      {label && (
        <label htmlFor={inputId} className="mb-1.5 block text-xs font-medium tracking-wide text-muted">
          {label}
          {required && (
            <span className="ml-0.5 text-critical" aria-hidden="true">
              *
            </span>
          )}
        </label>
      )}

      <div
        role="button"
        tabIndex={0}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            inputRef.current?.click();
          }
        }}
        onDragOver={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={handleDrop}
        className={cn(
          'flex cursor-pointer flex-col items-center justify-center gap-1.5 rounded-control border border-dashed px-4 py-6 text-center',
          'transition-colors duration-150',
          dragActive ? 'border-brand-500 bg-brand-500/5' : 'border-line hover:border-line-strong bg-surface-2',
          error && 'border-critical',
        )}
      >
        <span className="flex h-9 w-9 items-center justify-center rounded-full bg-surface-3 text-faint">
          <UploadCloud size={16} strokeWidth={1.75} />
        </span>
        <p className="text-xs font-medium text-content">{emptyLabel}</p>
        <p className="text-[11px] text-faint">
          {accept?.replace(/,/g, ', ')} &middot; up to {maxSizeMb}MB each
        </p>

        <input
          ref={inputRef}
          id={inputId}
          type="file"
          accept={accept}
          multiple={multiple}
          onChange={handleInputChange}
          className="sr-only"
        />
      </div>

      {files.length > 0 && preview === 'thumbnail' && (
        <ul className="mt-3 grid grid-cols-3 gap-2.5 sm:grid-cols-4">
          {files.map(({ id, file, previewUrl }) => (
            <li key={id} className="group relative aspect-square overflow-hidden rounded-control border border-line bg-surface-2">
              <img src={previewUrl} alt={file.name} className="h-full w-full object-cover" />
              <button
                type="button"
                onClick={() => removeFile(id)}
                aria-label={`Remove ${file.name}`}
                className="absolute right-1 top-1 flex h-5 w-5 items-center justify-center rounded-full bg-black/70 text-white opacity-0 transition-opacity group-hover:opacity-100 focus-visible:opacity-100"
              >
                <X size={11} strokeWidth={2.25} />
              </button>
            </li>
          ))}
        </ul>
      )}

      {files.length > 0 && preview === 'list' && (
        <ul className="mt-3 space-y-1.5">
          {files.map(({ id, file }) => (
            <li
              key={id}
              className="flex items-center gap-2.5 rounded-control border border-line bg-surface-2 px-3 py-2"
            >
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-control bg-surface-3 text-muted">
                {file.type.startsWith('image/') ? (
                  <ImageIcon size={13} strokeWidth={1.75} />
                ) : (
                  <FileText size={13} strokeWidth={1.75} />
                )}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-xs font-medium text-content">{file.name}</span>
                <span className="block text-[11px] text-faint">{formatBytes(file.size)}</span>
              </span>
              <button
                type="button"
                onClick={() => removeFile(id)}
                aria-label={`Remove ${file.name}`}
                className="shrink-0 text-faint transition-colors hover:text-critical"
              >
                <X size={14} strokeWidth={1.75} />
              </button>
            </li>
          ))}
        </ul>
      )}

      {(error || hint) && (
        <p className={cn('mt-1.5 text-xs', error ? 'text-critical' : 'text-faint')}>
          {error || hint}
        </p>
      )}
    </div>
  );
}
