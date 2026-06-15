import { render, screen } from '@testing-library/react'
import { test, expect } from 'vitest'
import { StatusBadge } from '@/components/recordings/StatusBadge'
import type { RecordingStatus } from '@/lib/types'

const LABELS: Array<[RecordingStatus, string]> = [
  ['queued',       'Queued'],
  ['transcribing', 'Transcribing'],
  ['diarizing',    'Diarizing'],
  ['embedding',    'Embedding'],
  ['ready',        'Ready'],
  ['failed',       'Failed'],
]

test.each(LABELS)('status=%s → label "%s" rendered', (status, label) => {
  render(<StatusBadge status={status} />)
  expect(screen.getByText(label)).toBeInTheDocument()
})

test('ready badge has success colour class', () => {
  render(<StatusBadge status="ready" />)
  expect(screen.getByText('Ready').closest('span')).toHaveClass('bg-success/[.13]')
})

test('failed badge has danger colour class', () => {
  render(<StatusBadge status="failed" />)
  expect(screen.getByText('Failed').closest('span')).toHaveClass('bg-danger/[.13]')
})

test('transcribing badge renders pulsing pip', () => {
  render(<StatusBadge status="transcribing" />)
  const pip = screen.getByText('Transcribing').closest('span')!.querySelector('span')
  expect(pip).toHaveClass('animate-pulse')
})

test('ready badge pip does NOT pulse', () => {
  render(<StatusBadge status="ready" />)
  const pip = screen.getByText('Ready').closest('span')!.querySelector('span')
  expect(pip).not.toHaveClass('animate-pulse')
})
