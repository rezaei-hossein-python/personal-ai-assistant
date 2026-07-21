import { useId } from 'react'
import type { KnowledgeMode } from '../api/types'

interface KnowledgeModeSelectorProps {
  disabled?: boolean
  mode: KnowledgeMode
  onChange: (mode: KnowledgeMode) => void
}

export function KnowledgeModeSelector({
  disabled = false,
  mode,
  onChange,
}: KnowledgeModeSelectorProps) {
  const helpId = useId()

  return (
    <label className="context-mode">
      <span>Knowledge</span>
      <select
        value={mode}
        onChange={(event) => onChange(event.target.value as KnowledgeMode)}
        disabled={disabled}
        aria-describedby={helpId}
      >
        <option value="auto">Auto</option>
        <option value="always">Always</option>
        <option value="never">Never</option>
      </select>
      <span className="visually-hidden" id={helpId}>
        Auto lets the assistant decide when to search documents. Always searches documents. Never
        skips document retrieval.
      </span>
    </label>
  )
}
