import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { test, expect, vi } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '../mocks/server'
import {
  BASE,
  MOCK_RECORDING_READY,
  MOCK_SEGMENTS,
  MOCK_SEGMENTS_WITH_SPEAKERS,
  MOCK_SEARCH_RESULTS,
} from '../mocks/handlers'
import RecordingDetailPage from '@/app/recordings/[id]/page'

const mockSeekTo = vi.hoisted(() => vi.fn())

vi.mock('@/components/player/AudioPlayer', () => ({
  AudioPlayer: () => <div data-testid="audio-player" />,
  useAudioPlayer: () => ({
    audioRef: { current: { play: vi.fn() } },
    currentTime: 0,
    isPlaying: false,
    duration: 0,
    seekTo: mockSeekTo,
  }),
}))

vi.mock('next/navigation', () => ({
  redirect: vi.fn(),
  useRouter: () => ({ push: vi.fn() }),
}))

vi.mock('@/components/auth/AuthProvider', () => ({
  useAuth: vi.fn(() => ({
    token: 'test-token',
    user: { id: '1', email: 'test@example.com', created_at: '2026-01-01' },
  })),
}))

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

const RID = MOCK_RECORDING_READY.id
const params = { id: RID }

function useWithSpeakers() {
  server.use(
    http.get(`${BASE}/recordings/${RID}`, () =>
      HttpResponse.json({
        ...MOCK_RECORDING_READY,
        source_type: 'upload',
        source_url: '/test.mp3',
        segments: MOCK_SEGMENTS_WITH_SPEAKERS,
      }),
    ),
  )
}

test('type query + submit → MSW returns 2 results → 2 result cards rendered', async () => {
  useWithSpeakers()
  wrap(<RecordingDetailPage params={params} />)
  await waitFor(() => screen.getByLabelText('Search recording'))
  await userEvent.type(screen.getByLabelText('Search recording'), 'gradient descent')
  await userEvent.click(screen.getByRole('button', { name: 'Search' }))
  await waitFor(() => screen.getByRole('list', { name: 'Search results' }))
  expect(
    within(screen.getByRole('list', { name: 'Search results' })).getAllByRole('listitem'),
  ).toHaveLength(2)
})

test('click result card → seekTo called with correct start_seconds', async () => {
  useWithSpeakers()
  wrap(<RecordingDetailPage params={params} />)
  await waitFor(() => screen.getByLabelText('Search recording'))
  await userEvent.type(screen.getByLabelText('Search recording'), 'gradient')
  await userEvent.click(screen.getByRole('button', { name: 'Search' }))
  await waitFor(() => screen.getByRole('list', { name: 'Search results' }))
  const firstCard = within(screen.getByRole('list', { name: 'Search results' })).getAllByRole('button')[0]
  await userEvent.click(firstCard)
  // MOCK_SEARCH_RESULTS.results[0].start_seconds = 30
  expect(mockSeekTo).toHaveBeenCalledWith(30)
})

test('click result card → matching transcript segment gets highlighted', async () => {
  useWithSpeakers()
  wrap(<RecordingDetailPage params={params} />)
  await waitFor(() => screen.getByLabelText('Search recording'))
  await userEvent.type(screen.getByLabelText('Search recording'), 'gradient')
  await userEvent.click(screen.getByRole('button', { name: 'Search' }))
  await waitFor(() => screen.getByRole('list', { name: 'Search results' }))
  const firstCard = within(screen.getByRole('list', { name: 'Search results' })).getAllByRole('button')[0]
  await userEvent.click(firstCard)
  // seg-2 is index 1 in MOCK_SEGMENTS_WITH_SPEAKERS; it is in MOCK_SEARCH_RESULTS
  const transcriptList = screen.getByRole('list', { name: 'Transcript' })
  expect(within(transcriptList).getAllByRole('listitem')[1]).toHaveClass('bg-[rgba(242,193,78,.15)]')
})

test('speaker filter visible when segments have mixed speaker labels', async () => {
  useWithSpeakers()
  wrap(<RecordingDetailPage params={params} />)
  await waitFor(() => screen.getByLabelText('Filter by speaker'))
})

test('speaker filter hidden when all speaker_label = null', async () => {
  server.use(
    http.get(`${BASE}/recordings/${RID}`, () =>
      HttpResponse.json({
        ...MOCK_RECORDING_READY,
        source_type: 'upload',
        source_url: '/test.mp3',
        segments: MOCK_SEGMENTS, // all speaker_label: null
      }),
    ),
  )
  wrap(<RecordingDetailPage params={params} />)
  await waitFor(() => screen.getByLabelText('Search recording'))
  expect(screen.queryByLabelText('Filter by speaker')).not.toBeInTheDocument()
})

test('search button disabled while search is in flight', async () => {
  useWithSpeakers()
  server.use(
    http.post(`${BASE}/recordings/${RID}/search`, async () => {
      await new Promise((r) => setTimeout(r, 150))
      return HttpResponse.json(MOCK_SEARCH_RESULTS)
    }),
  )
  wrap(<RecordingDetailPage params={params} />)
  await waitFor(() => screen.getByLabelText('Search recording'))
  await userEvent.type(screen.getByLabelText('Search recording'), 'gradient')
  userEvent.click(screen.getByRole('button', { name: 'Search' })) // no await — check mid-flight
  await waitFor(() => expect(screen.getByRole('button', { name: 'Searching…' })).toBeDisabled())
})
