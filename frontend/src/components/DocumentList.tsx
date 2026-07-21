import type { DocumentResponse } from '../api/types'

interface DocumentListProps {
  documents: DocumentResponse[]
  error: string | null
  isLoading: boolean
}

export function DocumentList({ documents, error, isLoading }: DocumentListProps) {
  return (
    <section className="document-list" aria-labelledby="document-list-title" aria-busy={isLoading}>
      <div className="document-list__header">
        <h2 id="document-list-title">Knowledge documents</h2>
        {isLoading ? (
          <span role="status">Loading documents...</span>
        ) : (
          <span>{getDocumentCountText(documents.length)}</span>
        )}
      </div>

      {error ? (
        <p className="document-error" role="alert">
          {error}
        </p>
      ) : null}

      {documents.length === 0 && !isLoading ? (
        <p className="document-list__empty">No documents uploaded.</p>
      ) : (
        <ul>
          {documents.map((document) => (
            <li key={document.id} className="document-list__item">
              <div>
                <span className="document-list__name">{document.original_filename}</span>
                {document.processing_status === 'failed' && document.error_message ? (
                  <span className="document-list__error">{document.error_message}</span>
                ) : null}
              </div>
              <span className={`document-status document-status--${document.processing_status}`}>
                {getDocumentStatusText(document.processing_status)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

function getDocumentCountText(count: number): string {
  return `${count} ${count === 1 ? 'document' : 'documents'} available`
}

function getDocumentStatusText(status: string): string {
  if (status === 'completed') {
    return 'Document processing completed'
  }

  if (status === 'failed') {
    return 'Document processing failed'
  }

  if (status === 'processing') {
    return 'Document processing'
  }

  return `Document status: ${status}`
}
