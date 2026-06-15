import type { RecordingStatus } from '@/lib/types'

export const TERMINAL_STATUSES: RecordingStatus[] = ['ready', 'failed']

export function formatTimestamp(seconds: number): string {
  const total = Math.floor(seconds)
  const m = Math.floor(total / 60).toString().padStart(2, '0')
  const s = (total % 60).toString().padStart(2, '0')
  return `${m}:${s}`
}

export function formatDuration(totalSeconds: number): string {
  const t = Math.floor(totalSeconds)
  const h = Math.floor(t / 3600)
  const m = Math.floor((t % 3600) / 60)
  const s = t % 60
  if (h > 0) {
    return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
  }
  return `${m}:${s.toString().padStart(2, '0')}`
}

export function getStatusRefetchInterval(status: RecordingStatus | undefined): number | false {
  if (!status || TERMINAL_STATUSES.includes(status)) return false
  return 3000
}
