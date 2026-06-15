import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { test, expect, vi } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '../mocks/server'
import { UploadButton } from '@/components/recordings/UploadButton'
import type { RecordingCreatedResponse } from '@/lib/types'

const ACCEPT = 'audio/mpeg,audio/wav,audio/mp4,audio/ogg,.mp3,.wav,.m4a,.ogg'

test('renders file input with correct accept attribute', () => {
  render(<UploadButton token="tok" onUploaded={vi.fn()} />)
  const input = document.querySelector('input[type="file"]')!
  expect(input).toHaveAttribute('accept', ACCEPT)
})

test('calls upload API and fires onUploaded on file select', async () => {
  const onUploaded = vi.fn<(recording: RecordingCreatedResponse) => void>()
  render(<UploadButton token="tok" onUploaded={onUploaded} />)

  const file = new File(['audio'], 'test.mp3', { type: 'audio/mpeg' })
  const input = document.querySelector('input[type="file"]') as HTMLInputElement
  await userEvent.upload(input, file)

  await waitFor(() =>
    expect(onUploaded).toHaveBeenCalledWith(
      expect.objectContaining({ status: 'queued' }),
    )
  )
})

test('disables button during upload (loading state)', async () => {
  server.use(
    http.post('*/recordings', async () => {
      await new Promise((r) => setTimeout(r, 50))
      return HttpResponse.json({ id: 'x', title: 'f.mp3', status: 'queued' }, { status: 201 })
    }),
  )
  render(<UploadButton token="tok" onUploaded={vi.fn()} />)
  const file = new File(['a'], 'f.mp3', { type: 'audio/mpeg' })
  const input = document.querySelector('input[type="file"]') as HTMLInputElement

  userEvent.upload(input, file)

  await waitFor(() => expect(screen.getByRole('button')).toBeDisabled())
})

test('shows error text when API returns 413', async () => {
  server.use(
    http.post('*/recordings', () =>
      HttpResponse.json(
        { error: { code: 'payload_too_large', message: 'File exceeds 50 MB limit' } },
        { status: 413 },
      )
    ),
  )
  render(<UploadButton token="tok" onUploaded={vi.fn()} />)
  const file = new File(['huge'], 'big.mp3', { type: 'audio/mpeg' })
  await userEvent.upload(document.querySelector('input[type="file"]') as HTMLInputElement, file)
  await waitFor(() =>
    expect(screen.getByRole('alert')).toHaveTextContent('File exceeds 50 MB limit')
  )
})

test('shows error text when API returns 415', async () => {
  server.use(
    http.post('*/recordings', () =>
      HttpResponse.json(
        { error: { code: 'unsupported_media_type', message: 'Unsupported file type' } },
        { status: 415 },
      )
    ),
  )
  render(<UploadButton token="tok" onUploaded={vi.fn()} />)
  // Use a valid audio MIME so userEvent doesn't filter it (accept-attribute check).
  // The backend rejection (415) is simulated by the MSW handler above.
  const file = new File(['x'], 'corrupted.mp3', { type: 'audio/mpeg' })
  await userEvent.upload(document.querySelector('input[type="file"]') as HTMLInputElement, file)
  await waitFor(() =>
    expect(screen.getByRole('alert')).toHaveTextContent('Unsupported file type')
  )
})
