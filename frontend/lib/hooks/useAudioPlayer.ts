'use client'

import { useCallback, useEffect, useRef, useState } from 'react'

export interface AudioPlayerControls {
  audioRef: React.RefObject<HTMLAudioElement>
  currentTime: number
  isPlaying: boolean
  duration: number
  seekTo: (seconds: number) => void
}

export function useAudioPlayer(): AudioPlayerControls {
  // useRef — not useState — so the element never triggers re-renders
  const audioRef = useRef<HTMLAudioElement>(null)
  const [currentTime, setCurrentTime] = useState(0)
  const [isPlaying, setIsPlaying] = useState(false)
  const [duration, setDuration] = useState(0)

  const seekTo = useCallback((seconds: number) => {
    if (audioRef.current) {
      audioRef.current.currentTime = seconds
    }
  }, [])

  useEffect(() => {
    const el = audioRef.current
    if (!el) return

    const onTimeUpdate = () => setCurrentTime(el.currentTime)
    const onPlay = () => setIsPlaying(true)
    const onPause = () => setIsPlaying(false)
    const onEnded = () => setIsPlaying(false)
    const onLoaded = () => setDuration(el.duration)

    el.addEventListener('timeupdate', onTimeUpdate)
    el.addEventListener('play', onPlay)
    el.addEventListener('pause', onPause)
    el.addEventListener('ended', onEnded)
    el.addEventListener('loadedmetadata', onLoaded)

    return () => {
      el.removeEventListener('timeupdate', onTimeUpdate)
      el.removeEventListener('play', onPlay)
      el.removeEventListener('pause', onPause)
      el.removeEventListener('ended', onEnded)
      el.removeEventListener('loadedmetadata', onLoaded)
    }
  }, [])

  return { audioRef, currentTime, isPlaying, duration, seekTo }
}
