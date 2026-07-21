import { useId, useRef, useState, type FormEvent, type RefCallback } from 'react'
import type { MemoryResponse } from '../api/types'

interface MemorySectionProps {
  error: string | null
  isCreating: boolean
  isDeleting: boolean
  isLoading: boolean
  memoryButtonRef?: (memoryId: number) => RefCallback<HTMLButtonElement>
  memories: MemoryResponse[]
  onCreate: (category: string, key: string, value: string) => Promise<boolean>
  onDelete: (memoryId: number) => void
}

export function MemorySection({
  error,
  isCreating,
  isDeleting,
  isLoading,
  memoryButtonRef,
  memories,
  onCreate,
  onDelete,
}: MemorySectionProps) {
  const categoryId = useId()
  const keyId = useId()
  const valueId = useId()
  const errorId = useId()
  const [category, setCategory] = useState('preference')
  const [key, setKey] = useState('')
  const [value, setValue] = useState('')
  const [validationError, setValidationError] = useState<string | null>(null)
  const keyInputRef = useRef<HTMLInputElement>(null)
  const isBusy = isCreating || isDeleting
  const formError = validationError ?? error

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (!category.trim() || !key.trim() || !value.trim()) {
      setValidationError('Enter a category, key, and memory value.')
      if (!category.trim()) {
        document.getElementById(categoryId)?.focus()
      } else if (!key.trim()) {
        keyInputRef.current?.focus()
      } else {
        document.getElementById(valueId)?.focus()
      }
      return
    }

    setValidationError(null)
    const created = await onCreate(category.trim(), key.trim(), value.trim())
    if (created) {
      setKey('')
      setValue('')
      window.setTimeout(() => keyInputRef.current?.focus(), 0)
    }
  }

  return (
    <section className="memory-section" aria-labelledby="memory-section-title">
      <form className="memory-form" onSubmit={handleSubmit} aria-busy={isBusy}>
        <div className="memory-form__fields">
          <label htmlFor={categoryId}>
            <span>Category</span>
            <input
              id={categoryId}
              value={category}
              onChange={(event) => {
                setCategory(event.target.value)
                setValidationError(null)
              }}
              disabled={isBusy}
              aria-describedby={formError ? errorId : undefined}
              aria-invalid={formError && !category.trim() ? true : undefined}
            />
          </label>
          <label htmlFor={keyId}>
            <span>Key</span>
            <input
              id={keyId}
              ref={keyInputRef}
              value={key}
              onChange={(event) => {
                setKey(event.target.value)
                setValidationError(null)
              }}
              disabled={isBusy}
              placeholder="favorite_language"
              aria-describedby={formError ? errorId : undefined}
              aria-invalid={formError && !key.trim() ? true : undefined}
            />
          </label>
          <label className="memory-form__value" htmlFor={valueId}>
            <span>Memory</span>
            <input
              id={valueId}
              value={value}
              onChange={(event) => {
                setValue(event.target.value)
                setValidationError(null)
              }}
              disabled={isBusy}
              placeholder="Python"
              aria-describedby={formError ? errorId : undefined}
              aria-invalid={formError && !value.trim() ? true : undefined}
            />
          </label>
        </div>
        <button type="submit" disabled={isBusy || !category.trim() || !key.trim() || !value.trim()}>
          Save memory
        </button>
      </form>

      {formError ? (
        <p className="memory-error" id={errorId} role="alert">
          {formError}
        </p>
      ) : null}

      <div className="memory-list">
        <div className="memory-list__header">
          <h2 id="memory-section-title">Memories</h2>
          <span>{getMemoryCountText(memories.length, isLoading)}</span>
        </div>

        {isLoading ? (
          <p className="memory-list__empty" role="status">
            Loading memories...
          </p>
        ) : memories.length === 0 ? (
          <p className="memory-list__empty">No saved memories.</p>
        ) : (
          <ul>
            {memories.map((memory) => (
              <li key={memory.id} className="memory-list__item">
                <div>
                  <span className="memory-list__key">
                    {memory.category} / {memory.key}
                  </span>
                  <span className="memory-list__value">{memory.value}</span>
                </div>
                <button
                  type="button"
                  onClick={() => onDelete(memory.id)}
                  disabled={isBusy}
                  ref={memoryButtonRef?.(memory.id)}
                  aria-label={`Delete memory: ${memory.category} / ${memory.key}`}
                >
                  Delete
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  )
}

function getMemoryCountText(count: number, isLoading: boolean): string {
  if (isLoading) {
    return 'Loading memories'
  }

  return `${count} ${count === 1 ? 'memory' : 'memories'} saved`
}
