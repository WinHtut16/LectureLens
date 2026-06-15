import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { test, expect, vi } from 'vitest'
import { MOCK_RECORDING_READY, MOCK_RECORDING_QUEUED } from '../mocks/handlers'
import RecordingsPage from '@/app/recordings/page'

vi.mock('next/navigation', () => ({
  useRouter: vi.fn(() => ({ push: vi.fn() })),
  redirect: vi.fn(),
}))

vi.mock('@/components/auth/AuthProvider', () => ({
  useAuth: vi.fn(() => ({
    token: 'test-token',
    user: { id: '1', email: 'u@u.com', created_at: '2026-01-01' },
    login: vi.fn(),
    logout: vi.fn(),
  })),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

test('shows all recordings returned by the API', async () => {
  wrap(<RecordingsPage />)
  await waitFor(() => {
    expect(screen.getByText(MOCK_RECORDING_READY.title)).toBeInTheDocument()
    expect(screen.getByText(MOCK_RECORDING_QUEUED.title)).toBeInTheDocument()
  })
})

test('redirects to /login when no token', async () => {
  const { redirect } = await import('next/navigation')
  const { useAuth } = await import('@/components/auth/AuthProvider')
  vi.mocked(useAuth).mockReturnValueOnce({
    token: null,
    user: null,
    login: vi.fn(),
    logout: vi.fn(),
  })
  wrap(<RecordingsPage />)
  await waitFor(() => expect(redirect).toHaveBeenCalledWith('/login'))
})

test('upload flow: select file → new queued card appears', async () => {
  wrap(<RecordingsPage />)
  await waitFor(() => screen.getByText(MOCK_RECORDING_READY.title))

  const file = new File(['audio'], 'new.mp3', { type: 'audio/mpeg' })
  const input = document.querySelector('input[type="file"]') as HTMLInputElement
  await userEvent.upload(input, file)

  await waitFor(() => expect(screen.getByText('new.mp3')).toBeInTheDocument())
})

test('non-terminal and terminal cards both render without error', async () => {
  wrap(<RecordingsPage />)
  await waitFor(() => {
    expect(screen.getByText('Ready')).toBeInTheDocument()
    expect(screen.getByText('Queued')).toBeInTheDocument()
  })
})

test('clicking a ready recording navigates to /recordings/{id}', async () => {
  const push = vi.fn()
  const { useRouter } = await import('next/navigation')
  vi.mocked(useRouter).mockReturnValue({ push, back: vi.fn(), forward: vi.fn(), refresh: vi.fn(), replace: vi.fn(), prefetch: vi.fn() } as ReturnType<typeof useRouter>)

  wrap(<RecordingsPage />)
  await waitFor(() => screen.getByText(MOCK_RECORDING_READY.title))
  const article = screen.getByText(MOCK_RECORDING_READY.title).closest('[role="article"]')!
  await userEvent.click(article)
  expect(push).toHaveBeenCalledWith(`/recordings/${MOCK_RECORDING_READY.id}`)
})
