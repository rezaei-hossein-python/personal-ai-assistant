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
  return (
    <label className="context-mode">
      <span>Memory</span>
      <select
        value={mode}
        onChange={(event) => onChange(event.target.value as MemoryMode)}
        disabled={disabled}
      >
        <option value="auto">Auto</option>
        <option value="always">Always</option>
        <option value="never">Never</option>
      </select>
    </label>
  )
}
