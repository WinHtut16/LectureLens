'use client'

import type React from 'react'
import { formatTimestamp, formatDuration } from '@/lib/utils'
import type { AudioPlayerControls } from '@/lib/hooks/useAudioPlayer'

export { useAudioPlayer } from '@/lib/hooks/useAudioPlayer'

interface Props extends AudioPlayerControls {
  src: string
  title?: string
}

export function AudioPlayer({ src, title, audioRef, currentTime, isPlaying, duration, seekTo }: Props) {
  function handleScrubberClick(e: React.MouseEvent<HTMLDivElement>) {
    if (duration === 0) return
    const rect = e.currentTarget.getBoundingClientRect()
    const fraction = (e.clientX - rect.left) / rect.width
    seekTo(fraction * duration)
  }

  function togglePlay() {
    const el = audioRef.current
    if (!el) return
    if (isPlaying) el.pause()
    else void el.play()
  }

  const progress = duration > 0 ? (currentTime / duration) * 100 : 0

  return (
    <div className="rounded-lg border border-border bg-surface px-5 py-4 space-y-3">
      <audio ref={audioRef} src={src} preload="metadata" className="hidden" aria-hidden />

      {title && (
        <p className="font-serif text-xl text-text leading-tight truncate">{title}</p>
      )}

      <div className="flex items-center gap-4">
        <button
          onClick={togglePlay}
          aria-label={isPlaying ? 'Pause' : 'Play'}
          className="w-[46px] h-[46px] rounded-full bg-primary-fill hover:bg-primary active:bg-primary-press flex items-center justify-center flex-shrink-0 shadow-glow transition-all active:scale-95"
        >
          {isPlaying ? (
            <svg width="16" height="16" viewBox="0 0 16 16" fill="white">
              <rect x="3" y="2" width="4" height="12" rx="1" />
              <rect x="9" y="2" width="4" height="12" rx="1" />
            </svg>
          ) : (
            <svg width="16" height="16" viewBox="0 0 16 16" fill="white">
              <path d="M5 3l9 5-9 5V3z" />
            </svg>
          )}
        </button>

        <div className="flex-1 space-y-1">
          <div
            role="slider"
            aria-label="Audio progress"
            aria-valuenow={Math.floor(currentTime)}
            aria-valuemin={0}
            aria-valuemax={Math.floor(duration)}
            className="relative h-[6px] bg-surface-2 rounded-full cursor-pointer"
            onClick={handleScrubberClick}
          >
            <div
              className="absolute inset-y-0 left-0 bg-primary rounded-full"
              style={{ width: `${progress}%` }}
            />
            <div
              className="absolute top-1/2 -translate-y-1/2 w-3 h-3 rounded-full bg-white shadow-glow"
              style={{ left: `calc(${progress}% - 6px)` }}
            />
          </div>
          <div className="flex justify-between text-xs font-mono text-text-faint">
            <span>{formatTimestamp(currentTime)}</span>
            {duration > 0 && <span>{formatDuration(duration)}</span>}
          </div>
        </div>
      </div>
    </div>
  )
}
