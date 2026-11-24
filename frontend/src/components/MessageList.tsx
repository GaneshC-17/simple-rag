import { useEffect, useRef } from 'react'
import type { ChatMessage } from '../types'
import SourceChip from './SourceChip'

interface MessageListProps {
  messages: ChatMessage[]
  pending: boolean
  onSuggestion: (question: string) => void
}

const SUGGESTIONS = ['What is heredity?', 'What determines inheritance?']

export default function MessageList({
  messages,
  pending,
  onSuggestion,
}: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, pending])

  if (messages.length === 0 && !pending) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center px-6 text-center">
        <h2 className="text-3xl font-semibold text-gray-900">Ask your documents</h2>
        <p className="mt-2 text-sm text-gray-500">
          Upload a PDF, then ask a question about it.
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-2">
          {SUGGESTIONS.map((suggestion) => (
            <button
              key={suggestion}
              type="button"
              onClick={() => onSuggestion(suggestion)}
              className="rounded-full border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
            >
              {suggestion}
            </button>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto px-6 py-8">
      <div className="mx-auto w-full max-w-3xl space-y-8">
        {messages.map((message) =>
          message.role === 'user' ? (
            <div key={message.id} className="flex justify-end">
              <div className="max-w-[80%] rounded-2xl bg-gray-100 px-4 py-3 text-sm text-gray-900">
                {message.text}
              </div>
            </div>
          ) : (
            <div key={message.id} className="text-sm leading-7 text-gray-800">
              <p className="mb-3 whitespace-pre-wrap">{message.text}</p>
              {message.sources && message.sources.length > 0 && (
                <div>
                  <p className="mb-2 text-xs font-medium uppercase tracking-wide text-gray-400">
                    Sources
                  </p>
                  {message.sources.map((source) => (
                    <SourceChip
                      key={`${source.source}-${source.chunk_index}`}
                      source={source}
                    />
                  ))}
                </div>
              )}
            </div>
          ),
        )}
        {pending && (
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <span className="animate-pulse">●</span> Thinking…
          </div>
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
