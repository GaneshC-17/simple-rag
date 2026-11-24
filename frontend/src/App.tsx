import { useEffect, useState } from 'react'
import { askQuestion, getHealth, indexPdf } from './api'
import Composer from './components/Composer'
import MessageList from './components/MessageList'
import MobileBar from './components/MobileBar'
import Sidebar from './components/Sidebar'
import type { ChatMessage } from './types'

export default function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const [online, setOnline] = useState(false)
  const [chunks, setChunks] = useState(0)

  useEffect(() => {
    let cancelled = false
    // The launcher opens the browser before Postgres may be ready - retry a few times.
    async function checkHealth(attempt: number) {
      try {
        const health = await getHealth()
        if (cancelled) return
        setOnline(health.status === 'ok')
        setChunks(health.chunks)
      } catch {
        if (cancelled) return
        if (attempt < 3) {
          window.setTimeout(() => void checkHealth(attempt + 1), 1500)
        } else {
          setOnline(false)
        }
      }
    }
    void checkHealth(1)
    return () => {
      cancelled = true
    }
  }, [])

  async function sendQuestion(question: string) {
    const text = question.trim()
    if (!text || pending) return

    setInput('')
    setError(null)
    setMessages((current) => [
      ...current,
      { id: crypto.randomUUID(), role: 'user', text },
    ])
    setPending(true)

    try {
      const result = await askQuestion(text)
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          text: result.answer,
          sources: result.sources,
        },
      ])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong')
    } finally {
      setPending(false)
    }
  }

  async function handleUpload(file: File) {
    setUploading(true)
    setError(null)
    setNotice(null)
    try {
      const result = await indexPdf(file)
      setNotice(`Indexed ${result.source}: ${result.chunks} chunks`)
      const health = await getHealth()
      setChunks(health.chunks)
      setOnline(health.status === 'ok')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  function newChat() {
    setMessages([])
    setInput('')
    setError(null)
    setNotice(null)
  }

  const barProps = {
    onNewChat: newChat,
    onUpload: handleUpload,
    uploading,
    online,
    chunks,
  }

  return (
    <div className="flex h-screen flex-col bg-white text-gray-900 md:flex-row">
      <Sidebar {...barProps} />
      <div className="flex min-w-0 flex-1 flex-col">
        <MobileBar {...barProps} />
        {error && (
          <div
            role="alert"
            className="mx-auto mt-4 w-full max-w-3xl rounded-lg bg-red-50 px-4 py-2 text-sm text-red-700"
          >
            {error}
          </div>
        )}
        {notice && (
          <div className="mx-auto mt-4 w-full max-w-3xl rounded-lg bg-green-50 px-4 py-2 text-sm text-green-700">
            {notice}
          </div>
        )}
        <MessageList
          messages={messages}
          pending={pending}
          onSuggestion={sendQuestion}
        />
        <Composer
          value={input}
          onChange={setInput}
          onSend={() => sendQuestion(input)}
          disabled={pending}
        />
      </div>
    </div>
  )
}
