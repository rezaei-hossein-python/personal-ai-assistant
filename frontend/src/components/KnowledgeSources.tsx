import type { ChatResponseMetadata, KnowledgeSource } from '../api/types'

interface KnowledgeSourcesProps {
  metadata?: ChatResponseMetadata | null
}

export function KnowledgeSources({ metadata }: KnowledgeSourcesProps) {
  const knowledge = metadata?.knowledge

  if (!knowledge) {
    return null
  }

  const showNoSources =
    knowledge.mode === 'explicit_enabled' &&
    knowledge.enabled &&
    knowledge.retrieval_count === 0 &&
    knowledge.sources.length === 0 &&
    !knowledge.warning

  if (!knowledge.warning && knowledge.sources.length === 0 && !showNoSources) {
    return null
  }

  return (
    <div className="knowledge-sources">
      {knowledge.warning ? (
        <p className="knowledge-sources__warning">{knowledge.warning}</p>
      ) : null}

      {knowledge.sources.length > 0 ? (
        <div>
          <span className="knowledge-sources__title">Sources</span>
          <ul>
            {knowledge.sources.map((source) => (
              <li key={`${source.document_id}-${source.chunk_id}`}>
                <span>{source.document_name}</span>
                <span>{formatSourceLocation(source)}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {showNoSources ? (
        <p className="knowledge-sources__empty">No document sources found.</p>
      ) : null}
    </div>
  )
}

function formatSourceLocation(source: KnowledgeSource): string {
  const section = `Section ${source.chunk_index + 1}`

  if (source.start_character === null || source.end_character === null) {
    return section
  }

  return `${section}, chars ${source.start_character}-${source.end_character}`
}
