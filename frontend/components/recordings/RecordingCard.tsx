'use client'

import { useEffect } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import type { RecordingListItem } from '@/lib/types'
import { getRecordingStatus } from '@/lib/api'
import { getStatusRefetchInterval, TERMINAL_STATUSES, formatDuration } from '@/lib/utils'
import { StatusBadge } from './StatusBadge'

interface Props {
  recording: RecordingListItem
  token: string
  onClick: (id: string) => void
}

function LensIcon({ ready }: { ready: boolean }) {
  return (
    <div
      className={`w-11 h-11 rounded-md flex items-center justify-center flex-shrink-0 border ${
        ready
          ? 'bg-[rgba(110,140,255,.12)] border-[rgba(110,140,255,.3)]'
          : 'bg-surface-2 border-border'
      }`}
    >
      <svg width="20" height="20" viewBox="0 0 26 26" fill="none">
        <circle cx="13" cy="13" r="11.25" stroke="#6e8cff" strokeWidth="1.5" />
        <circle cx="13" cy="13" r="6" stroke="#6e8cff" strokeWidth="1.5" opacity="0.55" />
        <circle cx="13" cy="13" r="2.4" fill="#6e8cff" />
      </svg>
    </div>
  )
}

export function RecordingCard({ recording, token, onClick }: Props) {
  const queryClient = useQueryClient()
  const isTerminal = TERMINAL_STATUSES.includes(recording.status)

  const { data: statusData } = useQuery({
    queryKey: ['recording-status', recording.id],
    queryFn: () => getRecordingStatus(token, recording.id),
    enabled: !isTerminal,
    refetchInterval: (query) => getStatusRefetchInterval(query.state.data?.status),
    initialData: isTerminal
      ? { id: recording.id, status: recording.status, error_message: recording.error_message }
      : undefined,
  })

  const currentStatus = statusData?.status ?? recording.status
  const errorMessage = statusData?.error_message ?? recording.error_message
  const isReady = currentStatus === 'ready'

  useEffect(() => {
    if (statusData?.status && TERMINAL_STATUSES.includes(statusData.status)) {
      queryClient.invalidateQueries({ queryKey: ['recordings'] })
    }
  }, [statusData?.status, queryClient])

  return (
    <div
      role="article"
      onClick={() => { if (isReady) onClick(recording.id) }}
      className={`group flex items-center gap-3 px-3 py-2.5 rounded-lg border transition-all ${
        isReady
          ? 'cursor-pointer hover:bg-surface-2 hover:border-border-strong hover:shadow-md'
          : 'opacity-60'
      } border-border`}
    >
      <LensIcon ready={isReady} />

      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-text truncate">{recording.title}</p>
        <p className="text-xs text-text-faint mt-0.5 font-mono">
          {recording.duration_seconds != null
            ? formatDuration(recording.duration_seconds)
            : new Date(recording.created_at).toLocaleDateString()}
        </p>
      </div>

      <StatusBadge status={currentStatus} />

      {currentStatus === 'failed' && errorMessage && (
        <details className="mt-1 w-full pl-14" onClick={(e) => e.stopPropagation()}>
          <summary className="text-xs text-danger cursor-pointer select-none">
            Show error
          </summary>
          <p className="text-xs text-danger/80 mt-1 break-words" role="alert">
            {errorMessage}
          </p>
        </details>
      )}
    </div>
  )
}
