import { useId } from 'react'
import type { MemoryMode } from '../api/types'

interface MemoryModeSelectorProps {
  disabled?: boolean
  mode: MemoryMode
  onChange: (mode: MemoryMode) => void
}

export function MemoryModeSelector({
  disabled = false,
  mode,
  onChange,
}: MemoryModeSelectorProps) {
  const helpId = useId()

  return (
    <label className="context-mode">
      <span>Memory</span>
      <select
        value={mode}
        onChange={(event) => onChange(event.target.value as MemoryMode)}
        disabled={disabled}
        aria-describedby={helpId}
      >
        <option value="auto">Auto</option>
        <option value="always">Always</option>
        <option value="never">Never</option>
      </select>
      <span className="visually-hidden" id={helpId}>
        Auto lets the assistant decide when to use saved memories. Always retrieves memories. Never
        skips memory retrieval.
      </span>
    </label>
  )
}
