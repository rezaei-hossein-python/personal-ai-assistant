import { forwardRef, useImperativeHandle, useRef, useState, type FormEvent } from 'react'

interface ChatInputProps {
  onSubmit: (message: string) => void
  disabled?: boolean
}

export interface ChatInputHandle {
  focus: () => void
}

export const ChatInput = forwardRef<ChatInputHandle, ChatInputProps>(function ChatInput(
  { disabled = false, onSubmit },
  ref,
) {
  const [message, setMessage] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)
  const trimmedMessage = message.trim()
  const isSubmitDisabled = disabled || trimmedMessage.length === 0

  useImperativeHandle(ref, () => ({
    focus: () => inputRef.current?.focus(),
  }))

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (isSubmitDisabled) {
      return
    }

    onSubmit(trimmedMessage)
    setMessage('')
  }

  return (
    <form className="chat-input" onSubmit={handleSubmit} aria-busy={disabled}>
      <label className="chat-input__label" htmlFor="chat-message">
        Message
      </label>
      <input
        ref={inputRef}
        id="chat-message"
        className="chat-input__field"
        type="text"
        value={message}
        onChange={(event) => setMessage(event.target.value)}
        placeholder="Type a message..."
        autoComplete="off"
        disabled={disabled}
      />
      <button className="chat-input__button" type="submit" disabled={isSubmitDisabled}>
        Send
      </button>
    </form>
  )
})
