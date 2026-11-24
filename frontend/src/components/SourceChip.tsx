import { useState } from 'react'
import type { Source } from '../types'

interface SourceChipProps {
  source: Source
}

export default function SourceChip({ source }: SourceChipProps) {
  const [open, setOpen] = useState(false)

  return (
    <div className="mb-2">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="rounded-full border border-gray-300 bg-white px-3 py-1 text-xs text-gray-600 hover:bg-gray-50"
      >
        chunk {source.chunk_index} · {source.similarity.toFixed(2)} {open ? '▴' : '▾'}
      </button>
      {open && (
        <div className="mt-2 rounded-lg border border-gray-200 bg-gray-50 p-3 text-xs text-gray-700">
          <p className="mb-2 font-medium text-gray-900">{source.source}</p>
          <pre className="max-h-64 overflow-auto whitespace-pre-wrap font-sans">
            {source.content}
          </pre>
        </div>
      )}
    </div>
  )
}
