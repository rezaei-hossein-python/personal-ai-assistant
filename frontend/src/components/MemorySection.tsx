import { useState, type FormEvent } from 'react'
import type { MemoryResponse } from '../api/types'

interface MemorySectionProps {
  error: string | null
  isCreating: boolean
  isDeleting: boolean
  isLoading: boolean
  memories: MemoryResponse[]
  onCreate: (category: string, key: string, value: string) => Promise<boolean>
  onDelete: (memoryId: number) => void
}

export function MemorySection({
  error,
  isCreating,
  isDeleting,
  isLoading,
  memories,
  onCreate,
  onDelete,
}: MemorySectionProps) {
  const [category, setCategory] = useState('preference')
  const [key, setKey] = useState('')
  const [value, setValue] = useState('')
  const isBusy = isCreating || isDeleting

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const created = await onCreate(category.trim(), key.trim(), value.trim())
    if (created) {
      setKey('')
      setValue('')
    }
  }

  return (
    <section className="memory-section" aria-label="Saved memories">
      <form className="memory-form" onSubmit={handleSubmit}>
        <div className="memory-form__fields">
          <label>
            <span>Category</span>
            <input
              value={category}
              onChange={(event) => setCategory(event.target.value)}
              disabled={isBusy}
            />
          </label>
          <label>
            <span>Key</span>
            <input
              value={key}
              onChange={(event) => setKey(event.target.value)}
              disabled={isBusy}
              placeholder="favorite_language"
            />
          </label>
          <label className="memory-form__value">
            <span>Memory</span>
            <input
              value={value}
              onChange={(event) => setValue(event.target.value)}
              disabled={isBusy}
              placeholder="Python"
            />
          </label>
        </div>
        <button type="submit" disabled={isBusy || !category.trim() || !key.trim() || !value.trim()}>
          Save
        </button>
      </form>

      {error ? (
        <p className="memory-error" role="alert">
          {error}
        </p>
      ) : null}

      <div className="memory-list">
        <div className="memory-list__header">
          <h2>Memories</h2>
          <span>{getMemoryCountText(memories.length, isLoading)}</span>
        </div>

        {isLoading ? (
          <p className="memory-list__empty">Loading memories...</p>
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
                  aria-label={`Delete memory ${memory.key}`}
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
    return 'Loading'
  }

  return `${count} saved`
}
