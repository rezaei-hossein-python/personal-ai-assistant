import type { DocumentResponse } from '../api/types'

interface DocumentListProps {
  documents: DocumentResponse[]
  error: string | null
  isLoading: boolean
}

export function DocumentList({ documents, error, isLoading }: DocumentListProps) {
  return (
    <section className="document-list" aria-label="Uploaded documents">
      <div className="document-list__header">
        <h2>Knowledge</h2>
        {isLoading ? <span>Loading...</span> : <span>{documents.length}</span>}
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
                {document.processing_status}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
