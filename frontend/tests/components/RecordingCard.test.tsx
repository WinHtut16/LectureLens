import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { test, expect, vi } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '../mocks/server'
import { RecordingCard } from '@/components/recordings/RecordingCard'
import type { RecordingListItem } from '@/lib/types'

const READY: RecordingListItem = {
  id: '1',
  title: 'lecture.mp3',
  status: 'ready',
  duration_seconds: 3600,
  error_message: null,
  created_at: '2026-01-01T00:00:00Z',
}

const QUEUED: RecordingListItem = {
  id: '2',
  title: 'processing.mp3',
  status: 'queued',
  duration_seconds: null,
  error_message: null,
  created_at: '2026-01-01T01:00:00Z',
}

const FAILED: RecordingListItem = {
  id: '3',
  title: 'broken.mp3',
  status: 'failed',
  duration_seconds: null,
  error_message: 'Transcription timed out',
  created_at: '2026-01-01T02:00:00Z',
}

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

test('renders title', () => {
  wrap(<RecordingCard recording={READY} token="tok" onClick={vi.fn()} />)
  expect(screen.getByText('lecture.mp3')).toBeInTheDocument()
})

test.each<[RecordingListItem, string]>([
  [READY,  'Ready'],
  [QUEUED, 'Queued'],
  [FAILED, 'Failed'],
])('shows correct status badge for %s status', (recording, label) => {
  server.use(
    http.get(`*/recordings/${recording.id}/status`, () =>
      HttpResponse.json({ id: recording.id, status: recording.status, error_message: null })
    )
  )
  wrap(<RecordingCard recording={recording} token="tok" onClick={vi.fn()} />)
  expect(screen.getByText(label)).toBeInTheDocument()
})

test('calls onClick with recording id when clicked and status=ready', async () => {
  const onClick = vi.fn()
  wrap(<RecordingCard recording={READY} token="tok" onClick={onClick} />)
  await userEvent.click(screen.getByRole('article'))
  expect(onClick).toHaveBeenCalledWith('1')
})

test('does NOT call onClick when status is non-terminal', async () => {
  server.use(
    http.get(`*/recordings/2/status`, () =>
      HttpResponse.json({ id: '2', status: 'queued', error_message: null })
    )
  )
  const onClick = vi.fn()
  wrap(<RecordingCard recording={QUEUED} token="tok" onClick={onClick} />)
  await userEvent.click(screen.getByRole('article'))
  expect(onClick).not.toHaveBeenCalled()
})

test('shows error message for failed recording', async () => {
  wrap(<RecordingCard recording={FAILED} token="tok" onClick={vi.fn()} />)
  await userEvent.click(screen.getByText('Show error'))
  expect(screen.getByRole('alert')).toHaveTextContent('Transcription timed out')
})
