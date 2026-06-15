'use client'

import { redirect, useRouter } from 'next/navigation'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '@/components/auth/AuthProvider'
import { getRecordings } from '@/lib/api'
import { RecordingCard } from '@/components/recordings/RecordingCard'
import { UploadButton } from '@/components/recordings/UploadButton'
import type { RecordingListItem, RecordingCreatedResponse } from '@/lib/types'

function Sidebar({ onLogout }: { onLogout: () => void }) {
  return (
    <aside className="w-[230px] flex-shrink-0 flex flex-col gap-1 border-r border-border px-4 py-6 min-h-screen">
      <div className="flex items-center gap-2.5 mb-6">
        <svg width="22" height="22" viewBox="0 0 26 26" fill="none">
          <circle cx="13" cy="13" r="11.25" stroke="#6e8cff" strokeWidth="1.5" />
          <circle cx="13" cy="13" r="6" stroke="#6e8cff" strokeWidth="1.5" opacity="0.55" />
          <circle cx="13" cy="13" r="2.4" fill="#6e8cff" />
        </svg>
        <span className="text-sm font-medium text-text">LectureLens</span>
      </div>

      <nav className="flex-1 space-y-0.5">
        <a
          href="/recordings"
          className="flex items-center gap-2.5 px-3 py-2 rounded-md text-sm font-medium text-text bg-surface-2 border border-border"
        >
          All recordings
        </a>
      </nav>

      <button
        onClick={onLogout}
        className="flex items-center gap-2 px-3 py-2 rounded-md text-sm text-text-muted hover:text-danger hover:bg-danger/[.08] transition-colors mt-auto"
      >
        Sign out
      </button>
    </aside>
  )
}

export default function RecordingsPage() {
  const { token, logout } = useAuth()
  const router = useRouter()
  const queryClient = useQueryClient()

  if (!token) redirect('/login')

  const { data: recordings, isLoading } = useQuery({
    queryKey: ['recordings'],
    queryFn: () => getRecordings(token),
    enabled: !!token,
  })

  function handleUploaded(created: RecordingCreatedResponse) {
    const optimistic: RecordingListItem = {
      id: created.id,
      title: created.title,
      status: created.status,
      duration_seconds: null,
      error_message: null,
      created_at: new Date().toISOString(),
    }
    queryClient.setQueryData<RecordingListItem[]>(['recordings'], (old = []) => [
      optimistic,
      ...old,
    ])
  }

  return (
    <div className="flex min-h-screen bg-bg">
      <Sidebar onLogout={logout} />

      <main className="flex-1 px-8 py-8 space-y-6 max-w-4xl">
        <div className="flex items-center justify-between">
          <h1 className="font-serif text-h2 text-text">All recordings</h1>
          <UploadButton token={token} onUploaded={handleUploaded} />
        </div>

        {isLoading && (
          <p className="text-sm text-text-muted">Loading recordings…</p>
        )}

        {recordings?.length === 0 && (
          <div className="mt-16 flex flex-col items-center justify-center border border-dashed border-border rounded-xl py-16 text-center space-y-3">
            <svg width="36" height="36" viewBox="0 0 26 26" fill="none" className="opacity-30">
              <circle cx="13" cy="13" r="11.25" stroke="#6e8cff" strokeWidth="1.5" />
              <circle cx="13" cy="13" r="6" stroke="#6e8cff" strokeWidth="1.5" opacity="0.55" />
              <circle cx="13" cy="13" r="2.4" fill="#6e8cff" />
            </svg>
            <p className="text-sm text-text-muted">No recordings yet</p>
            <p className="text-xs text-text-faint">Upload an audio file to get started</p>
          </div>
        )}

        <div className="space-y-1.5">
          {recordings?.map((recording) => (
            <RecordingCard
              key={recording.id}
              recording={recording}
              token={token}
              onClick={(id) => router.push(`/recordings/${id}`)}
            />
          ))}
        </div>
      </main>
    </div>
  )
}
