import { useRef } from 'react'

interface MobileBarProps {
  onNewChat: () => void
  onUpload: (file: File) => void
  uploading: boolean
  online: boolean
  chunks: number
}

export default function MobileBar({
  onNewChat,
  onUpload,
  uploading,
  online,
  chunks,
}: MobileBarProps) {
  const fileRef = useRef<HTMLInputElement>(null)

  return (
    <header className="flex items-center gap-2 border-b border-gray-200 bg-[#171717] px-4 py-3 text-gray-200 md:hidden">
      <span className="text-lg">✦</span>
      <span className="mr-auto font-semibold text-white">simple-rag</span>
      <button
        type="button"
        onClick={onNewChat}
        className="rounded-lg border border-gray-700 px-2 py-1 text-xs hover:bg-gray-800"
      >
        + New
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
        className="rounded-lg border border-gray-700 px-2 py-1 text-xs hover:bg-gray-800 disabled:opacity-50"
      >
        {uploading ? '…' : '↑ PDF'}
      </button>
      <span
        className={`h-2 w-2 rounded-full ${online ? 'bg-green-500' : 'bg-red-500'}`}
        title={online ? `${chunks} chunks indexed` : 'Offline'}
      />
    </header>
  )
}
