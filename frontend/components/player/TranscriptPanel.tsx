'use client'

import { useEffect, useRef } from 'react'
import type { Segment } from '@/lib/types'
import { formatTimestamp } from '@/lib/utils'

interface Props {
  segments: Segment[]
  currentTime: number
  onSegmentClick: (segment: Segment) => void
  highlightedIds?: Set<string>
}

function findActiveIndex(segments: Segment[], currentTime: number): number {
  return segments.findIndex(
    (s) => currentTime >= s.start_seconds && currentTime < s.end_seconds,
  )
}

export function TranscriptPanel({ segments, currentTime, onSegmentClick, highlightedIds }: Props) {
  const activeIndex = findActiveIndex(segments, currentTime)
  const containerRef = useRef<HTMLDivElement>(null)
  const activeRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    const container = containerRef.current
    const el = activeRef.current
    if (!container || !el || typeof container.scrollTo !== 'function') return
    const offset = el.offsetTop - container.offsetTop
    container.scrollTo({ top: offset - container.clientHeight / 3, behavior: 'smooth' })
  }, [activeIndex])

  return (
    <div
      ref={containerRef}
      role="list"
      aria-label="Transcript"
      className="overflow-y-auto max-h-[520px] space-y-0 pr-1"
    >
      {segments.map((seg, i) => {
        const isActive = i === activeIndex
        const isHighlighted = highlightedIds?.has(seg.id) ?? false

        let rowClass = 'hover:bg-surface-2'
        let borderClass = 'border-l-2 border-transparent'
        let timestampClass = 'text-text-faint'
        let textClass = 'text-text-muted'

        if (isActive) {
          rowClass = 'bg-surface-2'
          borderClass = 'border-l-2 border-primary'
          timestampClass = 'text-primary'
          textClass = 'text-text'
        } else if (isHighlighted) {
          rowClass = 'bg-[rgba(242,193,78,.15)]'
          borderClass = 'border-l-2 border-highlight'
          timestampClass = 'text-[#f5cf76]'
          textClass = 'text-text'
        }

        return (
          <button
            key={seg.id}
            ref={isActive ? activeRef : null}
            role="listitem"
            aria-current={isActive ? 'true' : undefined}
            onClick={() => onSegmentClick(seg)}
            className={`w-full text-left grid grid-cols-[64px_1fr] gap-4 px-3 py-2.5 ${rowClass} ${borderClass} transition-colors`}
          >
            <span className={`font-mono text-[12.5px] pt-0.5 ${timestampClass}`}>
              {formatTimestamp(seg.start_seconds)}
            </span>
            <span className={`text-sm leading-relaxed ${textClass}`}>
              {seg.text}
            </span>
          </button>
        )
      })}
    </div>
  )
}
