import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { test, expect, vi } from 'vitest'
import { SearchResults } from '@/components/SearchResults/SearchResults'
import type { SearchResult } from '@/lib/types'

const RESULTS: SearchResult[] = [
  { segment_id: 'seg-2', start_seconds: 90, end_seconds: 120, text: 'We will cover gradient descent today in class', score: 0.92, speaker_label: 'Professor' },
  { segment_id: 'seg-3', start_seconds: 125, end_seconds: 155, text: 'Any questions so far about the content?', score: 0.75, speaker_label: null },
]

const LONG_TEXT = 'a'.repeat(200)

test('loading state renders skeleton cards', () => {
  render(
    <SearchResults
      results={[]}
      queryTimeMs={0}
      isLoading={true}
      error={null}
      query="gradient"
      activeResultId={null}
      onResultClick={vi.fn()}
      onRetry={vi.fn()}
    />,
  )
  expect(screen.getByRole('status')).toBeInTheDocument()
})

test('empty state renders "No results for [query]" with actual query text', () => {
  render(
    <SearchResults
      results={[]}
      queryTimeMs={0}
      isLoading={false}
      error={null}
      query="overfitting"
      activeResultId={null}
      onResultClick={vi.fn()}
      onRetry={vi.fn()}
    />,
  )
  expect(screen.getByText(/No results for/)).toBeInTheDocument()
  expect(screen.getByText(/overfitting/)).toBeInTheDocument()
})

test('no output when query is empty and not loading', () => {
  const { container } = render(
    <SearchResults
      results={[]}
      queryTimeMs={0}
      isLoading={false}
      error={null}
      query=""
      activeResultId={null}
      onResultClick={vi.fn()}
      onRetry={vi.fn()}
    />,
  )
  expect(container).toBeEmptyDOMElement()
})

test('results render with correct mm:ss timestamp format', () => {
  render(
    <SearchResults
      results={RESULTS}
      queryTimeMs={312}
      isLoading={false}
      error={null}
      query="gradient"
      activeResultId={null}
      onResultClick={vi.fn()}
      onRetry={vi.fn()}
    />,
  )
  // 90s = 01:30, 125s = 02:05
  expect(screen.getByText('01:30')).toBeInTheDocument()
  expect(screen.getByText('02:05')).toBeInTheDocument()
})

test('clicking a result card calls onResultClick with correct result', async () => {
  const onResultClick = vi.fn()
  render(
    <SearchResults
      results={RESULTS}
      queryTimeMs={312}
      isLoading={false}
      error={null}
      query="gradient"
      activeResultId={null}
      onResultClick={onResultClick}
      onRetry={vi.fn()}
    />,
  )
  const list = screen.getByRole('list', { name: 'Search results' })
  const cards = within(list).getAllByRole('button')
  await userEvent.click(cards[0])
  expect(onResultClick).toHaveBeenCalledWith(RESULTS[0])
})

test('query_time_ms shown in results summary', () => {
  render(
    <SearchResults
      results={RESULTS}
      queryTimeMs={312}
      isLoading={false}
      error={null}
      query="gradient"
      activeResultId={null}
      onResultClick={vi.fn()}
      onRetry={vi.fn()}
    />,
  )
  expect(screen.getByText(/312ms/)).toBeInTheDocument()
})

test('long segment text is truncated at ~150 chars', () => {
  render(
    <SearchResults
      results={[{ ...RESULTS[0], text: LONG_TEXT }]}
      queryTimeMs={0}
      isLoading={false}
      error={null}
      query="test"
      activeResultId={null}
      onResultClick={vi.fn()}
      onRetry={vi.fn()}
    />,
  )
  const text = screen.getByRole('list').querySelector('p')!.textContent ?? ''
  expect(text.length).toBeLessThanOrEqual(154) // 150 chars + "…"
})

test('error state shows message and retry button', () => {
  const onRetry = vi.fn()
  render(
    <SearchResults
      results={[]}
      queryTimeMs={0}
      isLoading={false}
      error={new Error('Search failed')}
      query="gradient"
      activeResultId={null}
      onResultClick={vi.fn()}
      onRetry={onRetry}
    />,
  )
  expect(screen.getByText('Search failed')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument()
})

test('clicking retry calls onRetry', async () => {
  const onRetry = vi.fn()
  render(
    <SearchResults
      results={[]}
      queryTimeMs={0}
      isLoading={false}
      error={new Error('fail')}
      query="gradient"
      activeResultId={null}
      onResultClick={vi.fn()}
      onRetry={onRetry}
    />,
  )
  await userEvent.click(screen.getByRole('button', { name: 'Retry' }))
  expect(onRetry).toHaveBeenCalledOnce()
})

test('active result card has distinct styling', () => {
  render(
    <SearchResults
      results={RESULTS}
      queryTimeMs={312}
      isLoading={false}
      error={null}
      query="gradient"
      activeResultId="seg-2"
      onResultClick={vi.fn()}
      onRetry={vi.fn()}
    />,
  )
  const list = screen.getByRole('list', { name: 'Search results' })
  const activeCard = within(list).getAllByRole('button')[0]
  expect(activeCard).toHaveClass('border-primary')
})
