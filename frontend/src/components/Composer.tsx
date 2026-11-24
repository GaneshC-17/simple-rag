import type { FormEvent, KeyboardEvent } from 'react'

interface ComposerProps {
  value: string
  onChange: (value: string) => void
  onSend: () => void
  disabled: boolean
}

export default function Composer({
  value,
  onChange,
  onSend,
  disabled,
}: ComposerProps) {
  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      if (!disabled && value.trim()) onSend()
    }
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (!disabled && value.trim()) onSend()
  }

  return (
    <form onSubmit={handleSubmit} className="mx-auto w-full max-w-3xl px-6 pb-6">
      <div className="flex items-end gap-2 rounded-2xl border border-gray-300 bg-white p-2 shadow-sm focus-within:border-gray-500">
        <textarea
          rows={1}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask anything about your documents…"
          aria-label="Question"
          className="max-h-40 flex-1 resize-none bg-transparent px-3 py-2 text-sm outline-none placeholder:text-gray-400"
        />
        <button
          type="submit"
          disabled={disabled || !value.trim()}
          aria-label="Send question"
          className="flex h-9 w-9 items-center justify-center rounded-xl bg-gray-900 text-white hover:bg-gray-700 disabled:bg-gray-300"
        >
          ↑
        </button>
      </div>
      <p className="mt-2 text-center text-xs text-gray-400">
        Answers come only from your uploaded documents.
      </p>
    </form>
  )
}
