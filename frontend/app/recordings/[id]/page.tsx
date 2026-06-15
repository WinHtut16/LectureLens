'use client'

import { useMemo, useState } from 'react'
import { redirect, useRouter } from 'next/navigation'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useAuth } from '@/components/auth/AuthProvider'
import { getRecording, searchRecording } from '@/lib/api'
import { AudioPlayer, useAudioPlayer } from '@/components/player/AudioPlayer'
import { TranscriptPanel } from '@/components/player/TranscriptPanel'
import { SearchBar } from '@/components/SearchBar/SearchBar'
import { SearchResults } from '@/components/SearchResults/SearchResults'
import { StatusBadge } from '@/components/recordings/StatusBadge'
import { formatDuration } from '@/lib/utils'
import type { SearchResult, Segment } from '@/lib/types'

interface Props {
  params: { id: string }
}

export default function RecordingDetailPage({ params }: Props) {
  const { token } = useAuth()
  const router = useRouter()
  const player = useAudioPlayer()

  // Search state — lives here so both SearchResults and TranscriptPanel can read it
  const [searchQuery, setSearchQuery] = useState('')
  const [activeSegmentId, setActiveSegmentId] = useState<string | null>(null)

  if (!token) redirect('/login')

  const { data: recording, isLoading, error } = useQuery({
    queryKey: ['recording', params.id],
    queryFn: () => getRecording(token, params.id),
    enabled: !!token,
  })

  const {
    mutate: runSearch,
    data: searchData,
    isPending: isSearching,
    error: searchError,
    reset: resetSearch,
  } = useMutation({
    mutationFn: ({ query, speaker }: { query: string; speaker: string | null }) =>
      searchRecording(token, params.id, query, 10, speaker),
  })

  // Derive unique non-null speaker labels from segments
  const speakers = useMemo<string[]>(
    () => [
      ...new Set(
        (recording?.segments ?? [])
          .map((s) => s.speaker_label)
          .filter((l): l is string => l !== null),
      ),
    ],
    [recording],
  )

  function handleSearch(query: string, speakerLabel: string | null) {
    setSearchQuery(query)
    setActiveSegmentId(null)
    runSearch({ query, speaker: speakerLabel })
  }

  function handleSearchClear() {
    setSearchQuery('')
    setActiveSegmentId(null)
    resetSearch()
  }

  function handleResultClick(result: SearchResult) {
    setActiveSegmentId(result.segment_id)
    player.seekTo(result.start_seconds)
    void player.audioRef.current?.play()
  }

  function handleSegmentClick(segment: Segment) {
    player.seekTo(segment.start_seconds)
    void player.audioRef.current?.play()
  }

  if (isLoading) {
    return (
      <div className="flex min-h-screen bg-bg items-center justify-center">
        <p className="text-sm text-text-muted">Loading…</p>
      </div>
    )
  }

  if (error || !recording) {
    return (
      <div className="flex min-h-screen bg-bg items-center justify-center">
        <p className="text-sm text-danger">Recording not found.</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-bg">
      {/* Top bar */}
      <header className="sticky top-0 z-10 flex items-center gap-3 px-6 py-3 bg-bg/90 backdrop-blur border-b border-border">
        <button
          onClick={() => router.push('/recordings')}
          className="text-text-muted hover:text-text transition-colors text-sm flex items-center gap-1.5"
        >
          <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
          Recordings
        </button>
        <span className="text-text-faint">/</span>
        <span className="text-sm text-text truncate max-w-[260px]">{recording.title}</span>
        <StatusBadge status={recording.status} />
        {recording.duration_seconds != null && (
          <span className="text-xs font-mono text-text-faint ml-auto">
            {formatDuration(recording.duration_seconds)}
          </span>
        )}
      </header>

      <div className="max-w-[760px] mx-auto px-4 py-6 space-y-6">

        {/* Audio player — sticky below header */}
        {recording.status === 'ready' && (
          <div className="sticky top-[53px] z-[5]">
            <AudioPlayer
              src={recording.source_url ?? ''}
              title={recording.title}
              {...player}
            />
          </div>
        )}

        {/* Processing state */}
        {recording.status !== 'ready' && recording.status !== 'failed' && (
          <div className="rounded-xl border border-dashed border-border py-12 text-center space-y-3">
            <p className="text-sm text-text-muted">Your recording is being processed</p>
            <p className="text-xs text-text-faint">
              This can take a few minutes — the page will update when ready.
            </p>
            <div className="flex items-center justify-center mt-3">
              <StatusBadge status={recording.status} />
            </div>
          </div>
        )}

        {/* Failed state */}
        {recording.status === 'failed' && (
          <div className="rounded-xl border border-danger/[.32] bg-danger/[.08] px-5 py-4 space-y-1">
            <p className="text-sm font-medium text-danger">Processing failed</p>
            {recording.error_message && (
              <p className="text-xs text-danger/80">{recording.error_message}</p>
            )}
          </div>
        )}

        {/* Search — only when recording is ready */}
        {recording.status === 'ready' && (
          <section aria-label="Search">
            <SearchBar
              onSearch={handleSearch}
              onClear={handleSearchClear}
              isLoading={isSearching}
              speakers={speakers}
            />
            {(searchQuery || isSearching) && (
              <div className="mt-4">
                <SearchResults
                  results={searchData?.results ?? []}
                  queryTimeMs={searchData?.query_time_ms ?? 0}
                  isLoading={isSearching}
                  error={searchError as Error | null}
                  query={searchQuery}
                  activeResultId={activeSegmentId}
                  onResultClick={handleResultClick}
                  onRetry={() => runSearch({ query: searchQuery, speaker: null })}
                />
              </div>
            )}
          </section>
        )}

        {/* Transcript */}
        {recording.status === 'ready' && recording.segments.length > 0 && (
          <section aria-label="Transcript">
            <h2 className="text-xs font-medium text-text-faint uppercase tracking-wider mb-3">
              Transcript
            </h2>
            <TranscriptPanel
              segments={recording.segments}
              currentTime={player.currentTime}
              onSegmentClick={handleSegmentClick}
              highlightedIds={
                searchData ? new Set(searchData.results.map((r) => r.segment_id)) : undefined
              }
            />
          </section>
        )}

        {recording.status === 'ready' && recording.segments.length === 0 && (
          <p className="text-sm text-text-muted text-center py-12">No transcript available.</p>
        )}
      </div>
    </div>
  )
}
