'use client'

import { useRef, useState } from 'react'
import { SpeakerFilter } from '@/components/SpeakerFilter/SpeakerFilter'

interface Props {
  onSearch: (query: string, speakerLabel: string | null) => void
  onClear: () => void
  isLoading: boolean
  speakers: string[]
}

export function SearchBar({ onSearch, onClear, isLoading, speakers }: Props) {
  const [query, setQuery] = useState('')
  const [selectedSpeaker, setSelectedSpeaker] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  function handleSubmit() {
    const trimmed = query.trim()
    if (!trimmed || isLoading) return
    onSearch(trimmed, selectedSpeaker)
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') handleSubmit()
  }

  function handleClear() {
    setQuery('')
    setSelectedSpeaker(null)
    onClear()
    inputRef.current?.focus()
  }

  return (
    <div className="flex gap-2 flex-wrap items-center">
      <div className="relative flex-1 min-w-0">
        <input
          ref={inputRef}
          type="text"
          aria-label="Search recording"
          placeholder="Search by meaning…"
          maxLength={256}
          value={query}
          disabled={isLoading}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          className="w-full rounded-lg border border-border bg-surface px-3 py-2 pr-8 text-sm text-text placeholder:text-text-faint focus:outline-none focus:ring-2 focus:ring-primary/40 disabled:opacity-50"
        />
        {query && (
          <button
            type="button"
            aria-label="Clear search"
            onClick={handleClear}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-lg leading-none text-text-faint hover:text-text"
          >
            ×
          </button>
        )}
      </div>
      <SpeakerFilter
        speakers={speakers}
        selected={selectedSpeaker}
        onChange={setSelectedSpeaker}
      />
      <button
        type="button"
        disabled={!query.trim() || isLoading}
        onClick={handleSubmit}
        className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-40 disabled:cursor-not-allowed transition-opacity"
      >
        {isLoading ? 'Searching…' : 'Search'}
      </button>
    </div>
  )
}
