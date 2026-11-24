import { useRef } from 'react'

interface SidebarProps {
  onNewChat: () => void
  onUpload: (file: File) => void
  uploading: boolean
  online: boolean
  chunks: number
}

export default function Sidebar({
  onNewChat,
  onUpload,
  uploading,
  online,
  chunks,
}: SidebarProps) {
  const fileRef = useRef<HTMLInputElement>(null)

  return (
    <aside className="hidden h-full w-64 shrink-0 flex-col bg-[#171717] p-4 text-gray-200 md:flex">
      <div className="mb-8 flex items-center gap-2">
        <span className="text-xl">✦</span>
        <h1 className="text-lg font-semibold tracking-tight text-white">simple-rag</h1>
      </div>

      <button
        type="button"
        onClick={onNewChat}
        className="mb-3 rounded-lg border border-gray-700 px-3 py-2 text-left text-sm hover:bg-gray-800"
      >
        + New chat
      </button>

      <input
        ref={fileRef}
        type="file"
        accept="application/pdf,.pdf"
        className="hidden"
        onChange={(event) => {
          const file = event.target.files?.[0]
          if (file) onUpload(file)
          event.target.value = ''
        }}
      />
      <button
        type="button"
        disabled={uploading}
        onClick={() => fileRef.current?.click()}
        className="rounded-lg border border-gray-700 px-3 py-2 text-left text-sm hover:bg-gray-800 disabled:opacity-50"
      >
        {uploading ? 'Indexing…' : '↑ Upload PDF'}
      </button>

      <div className="mt-auto flex items-center gap-2 border-t border-gray-800 pt-4 text-xs text-gray-400">
        <span
          className={`h-2 w-2 rounded-full ${online ? 'bg-green-500' : 'bg-red-500'}`}
        />
        <span>{online ? `Online · ${chunks} chunks` : 'Offline'}</span>
      </div>
    </aside>
  )
}
