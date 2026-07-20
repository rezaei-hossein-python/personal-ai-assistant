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
  return (
    <label className="knowledge-mode">
      <span>Knowledge</span>
      <select
        value={mode}
        onChange={(event) => onChange(event.target.value as KnowledgeMode)}
        disabled={disabled}
      >
        <option value="auto">Auto</option>
        <option value="always">Always</option>
        <option value="never">Never</option>
      </select>
    </label>
  )
}
