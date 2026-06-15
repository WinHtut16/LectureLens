'use client'

import { useRef, useState } from 'react'
import { uploadRecording, ApiError } from '@/lib/api'
import type { RecordingCreatedResponse } from '@/lib/types'

const ACCEPT = 'audio/mpeg,audio/wav,audio/mp4,audio/ogg,.mp3,.wav,.m4a,.ogg'

interface Props {
  token: string
  onUploaded: (recording: RecordingCreatedResponse) => void
}

export function UploadButton({ token, onUploaded }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setError(null)
    setLoading(true)
    try {
      const result = await uploadRecording(token, file)
      onUploaded(result)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Upload failed. Please try again.')
    } finally {
      setLoading(false)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT}
        className="sr-only"
        id="upload-input"
        onChange={handleChange}
        disabled={loading}
      />
      <button
        type="button"
        disabled={loading}
        onClick={() => inputRef.current?.click()}
        className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-primary-fill hover:bg-primary active:bg-primary-press text-white text-sm font-medium disabled:opacity-50 transition-colors active:scale-[.98]"
      >
        {loading ? (
          <>
            <svg className="animate-spin w-3.5 h-3.5" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
            Uploading…
          </>
        ) : (
          <>
            <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M12 3v13M8 7l4-4 4 4" />
            </svg>
            Upload recording
          </>
        )}
      </button>
      {error && (
        <p role="alert" className="text-xs text-danger">{error}</p>
      )}
    </div>
  )
}
