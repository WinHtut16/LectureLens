'use client'

import { formatTimestamp } from '@/lib/utils'
import type { SearchResult } from '@/lib/types'

interface Props {
  results: SearchResult[]
  queryTimeMs: number
  isLoading: boolean
  error: Error | null
  query: string
  activeResultId: string | null
  onResultClick: (result: SearchResult) => void
  onRetry: () => void
}

const MAX_TEXT = 150

function truncate(text: string): string {
  return text.length > MAX_TEXT ? text.slice(0, MAX_TEXT) + '…' : text
}

export function SearchResults({
  results,
  queryTimeMs,
  isLoading,
  error,
  query,
  activeResultId,
  onResultClick,
  onRetry,
}: Props) {
  if (!query && !isLoading) return null

  if (isLoading) {
    return (
      <div role="status" aria-label="Search results loading" className="space-y-2">
        {[0, 1, 2].map((i) => (
          <div key={i} className="animate-pulse h-[72px] rounded-lg bg-surface-2" />
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-between rounded-lg border border-danger/30 bg-danger/5 px-4 py-3">
        <p className="text-sm text-danger">{error.message}</p>
        <button
          type="button"
          onClick={onRetry}
          className="ml-4 text-sm text-primary hover:underline"
        >
          Retry
        </button>
      </div>
    )
  }

  if (results.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-text-muted">
        No results for <span className="font-medium text-text">&ldquo;{query}&rdquo;</span>
      </p>
    )
  }

  return (
    <div>
      <p className="mb-3 text-xs text-text-faint">
        {results.length} result{results.length !== 1 ? 's' : ''} · {queryTimeMs}ms
      </p>
      <ul role="list" aria-label="Search results" className="space-y-2">
        {results.map((result) => {
          const isActive = result.segment_id === activeResultId
          return (
            <li key={result.segment_id} role="listitem">
              <button
                type="button"
                onClick={() => onResultClick(result)}
                className={`w-full rounded-lg border px-4 py-3 text-left transition-colors ${
                  isActive
                    ? 'border-primary bg-primary/5'
                    : 'border-border bg-surface hover:bg-surface-2'
                }`}
              >
                <div className="mb-1.5 flex items-center gap-3">
                  <span className="font-mono text-xs text-primary">
                    {formatTimestamp(result.start_seconds)}
                  </span>
                  {result.speaker_label && (
                    <span className="rounded bg-surface-2 px-1.5 py-0.5 text-xs text-text-faint">
                      {result.speaker_label}
                    </span>
                  )}
                  <span
                    className="ml-auto h-1 w-16 overflow-hidden rounded-full bg-surface-2"
                    aria-hidden="true"
                  >
                    <span
                      className="block h-full rounded-full bg-primary/50"
                      style={{ width: `${Math.round(result.score * 100)}%` }}
                    />
                  </span>
                </div>
                <p className="text-sm leading-relaxed text-text">{truncate(result.text)}</p>
              </button>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
