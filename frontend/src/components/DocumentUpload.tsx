import { useState, type ChangeEvent, type FormEvent } from 'react'

const supportedExtensions = ['.pdf', '.docx', '.txt', '.md', '.markdown']
const supportedMimeTypes = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'text/plain',
  'text/markdown',
  'text/x-markdown',
]

interface DocumentUploadProps {
  disabled?: boolean
  error: string | null
  isUploading: boolean
  onUpload: (file: File) => void
}

export function DocumentUpload({
  disabled = false,
  error,
  isUploading,
  onUpload,
}: DocumentUploadProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [validationError, setValidationError] = useState<string | null>(null)
  const isDisabled = disabled || isUploading

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null
    setSelectedFile(file)
    setValidationError(file && !isSupportedFile(file) ? 'Use PDF, DOCX, TXT, or Markdown.' : null)
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (!selectedFile || isDisabled) {
      return
    }

    if (!isSupportedFile(selectedFile)) {
      setValidationError('Use PDF, DOCX, TXT, or Markdown.')
      return
    }

    setValidationError(null)
    onUpload(selectedFile)
  }

  return (
    <form className="document-upload" onSubmit={handleSubmit}>
      <label className="document-upload__label" htmlFor="document-upload">
        Documents
      </label>
      <div className="document-upload__controls">
        <input
          id="document-upload"
          type="file"
          accept=".pdf,.docx,.txt,.md,.markdown,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,text/markdown,text/x-markdown"
          onChange={handleFileChange}
          disabled={isDisabled}
        />
        <button type="submit" disabled={isDisabled || !selectedFile || validationError !== null}>
          {isUploading ? 'Uploading...' : 'Upload'}
        </button>
      </div>
      <p className="document-upload__hint">PDF, DOCX, TXT, Markdown</p>
      {validationError ? (
        <p className="document-error" role="alert">
          {validationError}
        </p>
      ) : null}
      {error ? (
        <p className="document-error" role="alert">
          {error}
        </p>
      ) : null}
    </form>
  )
}

function isSupportedFile(file: File): boolean {
  const lowerName = file.name.toLowerCase()
  const hasSupportedExtension = supportedExtensions.some((extension) =>
    lowerName.endsWith(extension),
  )

  return hasSupportedExtension || supportedMimeTypes.includes(file.type)
}
