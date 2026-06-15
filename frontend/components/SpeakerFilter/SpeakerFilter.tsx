'use client'

interface Props {
  speakers: string[]
  selected: string | null
  onChange: (speaker: string | null) => void
}

export function SpeakerFilter({ speakers, selected, onChange }: Props) {
  if (speakers.length < 2) return null

  return (
    <select
      aria-label="Filter by speaker"
      value={selected ?? ''}
      onChange={(e) => onChange(e.target.value === '' ? null : e.target.value)}
      className="text-sm border border-border rounded-lg px-2.5 py-1.5 bg-surface text-text focus:outline-none focus:ring-2 focus:ring-primary/40"
    >
      <option value="">All speakers</option>
      {speakers.map((s) => (
        <option key={s} value={s}>
          {s}
        </option>
      ))}
    </select>
  )
}
