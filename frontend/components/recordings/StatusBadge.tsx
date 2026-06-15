import type { RecordingStatus } from '@/lib/types'

interface BadgeConfig {
  label: string
  wrapperClass: string
  pipClass: string
  pulse?: boolean
}

const CONFIG: Record<RecordingStatus, BadgeConfig> = {
  queued: {
    label: 'Queued',
    wrapperClass: 'bg-surface-2 text-text-muted border border-border',
    pipClass: 'bg-text-faint',
  },
  transcribing: {
    label: 'Transcribing',
    wrapperClass: 'bg-[rgba(242,193,78,.13)] text-[#f5cf76] border border-warn/[.32]',
    pipClass: 'bg-warn',
    pulse: true,
  },
  diarizing: {
    label: 'Diarizing',
    wrapperClass: 'bg-[rgba(242,193,78,.13)] text-[#f5cf76] border border-warn/[.32]',
    pipClass: 'bg-warn',
    pulse: true,
  },
  embedding: {
    label: 'Embedding',
    wrapperClass: 'bg-[rgba(242,193,78,.13)] text-[#f5cf76] border border-warn/[.32]',
    pipClass: 'bg-warn',
    pulse: true,
  },
  ready: {
    label: 'Ready',
    wrapperClass: 'bg-success/[.13] text-[#6fe0bb] border border-success/[.3]',
    pipClass: 'bg-success',
  },
  failed: {
    label: 'Failed',
    wrapperClass: 'bg-danger/[.13] text-[#ffa1a1] border border-danger/[.32]',
    pipClass: 'bg-danger',
  },
}

export function StatusBadge({ status }: { status: RecordingStatus }) {
  const { label, wrapperClass, pipClass, pulse } = CONFIG[status]
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-xs font-mono ${wrapperClass}`}
    >
      <span
        className={`w-[5px] h-[5px] rounded-full flex-shrink-0 ${pipClass} ${pulse ? 'animate-pulse' : ''}`}
      />
      {label}
    </span>
  )
}
