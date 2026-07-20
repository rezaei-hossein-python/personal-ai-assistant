import { useState, type FormEvent } from 'react'

interface ChatInputProps {
  onSubmit: (message: string) => void
  disabled?: boolean
}

export function ChatInput({ disabled = false, onSubmit }: ChatInputProps) {
  const [message, setMessage] = useState('')
  const trimmedMessage = message.trim()
  const isSubmitDisabled = disabled || trimmedMessage.length === 0

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (isSubmitDisabled) {
      return
    }

    onSubmit(trimmedMessage)
    setMessage('')
  }

  return (
    <form className="chat-input" onSubmit={handleSubmit}>
      <label className="chat-input__label" htmlFor="chat-message">
        Message
      </label>
      <input
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
}
