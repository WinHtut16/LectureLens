import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { test, expect, vi } from 'vitest'
import { TranscriptPanel } from '@/components/player/TranscriptPanel'
import type { Segment } from '@/lib/types'

const SEGMENTS: Segment[] = [
  { id: 'a', segment_index: 0, start_seconds: 0,  end_seconds: 20, text: 'First segment text',  speaker_label: null },
  { id: 'b', segment_index: 1, start_seconds: 30, end_seconds: 60, text: 'Second segment text', speaker_label: null },
  { id: 'c', segment_index: 2, start_seconds: 60, end_seconds: 90, text: 'Third segment text',  speaker_label: null },
]

test('renders all segments with formatted timestamps', () => {
  render(<TranscriptPanel segments={SEGMENTS} currentTime={0} onSegmentClick={vi.fn()} />)
  expect(screen.getByText('First segment text')).toBeInTheDocument()
  expect(screen.getByText('Second segment text')).toBeInTheDocument()
  expect(screen.getByText('Third segment text')).toBeInTheDocument()
  expect(screen.getByText('00:00')).toBeInTheDocument()
  expect(screen.getByText('00:30')).toBeInTheDocument()
  expect(screen.getByText('01:00')).toBeInTheDocument()
})

test('highlights correct segment when currentTime=45 (inside second segment 30–60)', () => {
  render(<TranscriptPanel segments={SEGMENTS} currentTime={45} onSegmentClick={vi.fn()} />)
  const items = screen.getAllByRole('listitem')
  expect(items[0]).not.toHaveAttribute('aria-current', 'true')
  expect(items[1]).toHaveAttribute('aria-current', 'true')
  expect(items[2]).not.toHaveAttribute('aria-current', 'true')
})

test('calls onSegmentClick with the full segment object when clicked', async () => {
  const onClick = vi.fn()
  render(<TranscriptPanel segments={SEGMENTS} currentTime={0} onSegmentClick={onClick} />)
  await userEvent.click(screen.getByText('Second segment text'))
  expect(onClick).toHaveBeenCalledWith(SEGMENTS[1])
})

test('no segment is highlighted when currentTime falls in the gap (20–30 s)', () => {
  render(<TranscriptPanel segments={SEGMENTS} currentTime={25} onSegmentClick={vi.fn()} />)
  const items = screen.getAllByRole('listitem')
  items.forEach((item) => {
    expect(item).not.toHaveAttribute('aria-current', 'true')
  })
})

test('no segment highlighted when currentTime is past all segments', () => {
  render(<TranscriptPanel segments={SEGMENTS} currentTime={100} onSegmentClick={vi.fn()} />)
  const items = screen.getAllByRole('listitem')
  items.forEach((item) => {
    expect(item).not.toHaveAttribute('aria-current', 'true')
  })
})
