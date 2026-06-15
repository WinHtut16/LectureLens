import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { test, expect, vi } from 'vitest'
import { SearchBar } from '@/components/SearchBar/SearchBar'

test('renders input and submit button', () => {
  render(<SearchBar onSearch={vi.fn()} onClear={vi.fn()} isLoading={false} speakers={[]} />)
  expect(screen.getByRole('textbox', { name: 'Search recording' })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Search' })).toBeInTheDocument()
})

test('submit on Enter fires onSearch with trimmed query', async () => {
  const onSearch = vi.fn()
  render(<SearchBar onSearch={onSearch} onClear={vi.fn()} isLoading={false} speakers={[]} />)
  await userEvent.type(screen.getByRole('textbox'), '  gradient descent  {Enter}')
  expect(onSearch).toHaveBeenCalledWith('gradient descent', null)
})

test('submit on button click fires onSearch', async () => {
  const onSearch = vi.fn()
  render(<SearchBar onSearch={onSearch} onClear={vi.fn()} isLoading={false} speakers={[]} />)
  await userEvent.type(screen.getByRole('textbox'), 'overfitting')
  await userEvent.click(screen.getByRole('button', { name: 'Search' }))
  expect(onSearch).toHaveBeenCalledWith('overfitting', null)
})

test('empty/whitespace-only query does NOT fire onSearch', async () => {
  const onSearch = vi.fn()
  render(<SearchBar onSearch={onSearch} onClear={vi.fn()} isLoading={false} speakers={[]} />)
  await userEvent.type(screen.getByRole('textbox'), '   {Enter}')
  expect(onSearch).not.toHaveBeenCalled()
  await userEvent.click(screen.getByRole('button', { name: 'Search' }))
  expect(onSearch).not.toHaveBeenCalled()
})

test('input enforces maxLength of 256 characters', () => {
  render(<SearchBar onSearch={vi.fn()} onClear={vi.fn()} isLoading={false} speakers={[]} />)
  expect(screen.getByRole('textbox')).toHaveAttribute('maxLength', '256')
})

test('disabled state: input and button both disabled while isLoading=true', () => {
  render(<SearchBar onSearch={vi.fn()} onClear={vi.fn()} isLoading={true} speakers={[]} />)
  expect(screen.getByRole('textbox')).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Searching…' })).toBeDisabled()
})

test('clearing input via X button calls onClear', async () => {
  const onClear = vi.fn()
  render(<SearchBar onSearch={vi.fn()} onClear={onClear} isLoading={false} speakers={[]} />)
  await userEvent.type(screen.getByRole('textbox'), 'hello')
  await userEvent.click(screen.getByRole('button', { name: 'Clear search' }))
  expect(onClear).toHaveBeenCalledOnce()
  expect(screen.getByRole('textbox')).toHaveValue('')
})

test('SpeakerFilter rendered when 2+ distinct speakers provided', () => {
  render(
    <SearchBar
      onSearch={vi.fn()}
      onClear={vi.fn()}
      isLoading={false}
      speakers={['Speaker 1', 'Speaker 2']}
    />,
  )
  expect(screen.getByRole('combobox', { name: 'Filter by speaker' })).toBeInTheDocument()
})

test('SpeakerFilter NOT rendered when speakers list is empty', () => {
  render(<SearchBar onSearch={vi.fn()} onClear={vi.fn()} isLoading={false} speakers={[]} />)
  expect(screen.queryByRole('combobox')).not.toBeInTheDocument()
})

test('selected speaker included in onSearch call', async () => {
  const onSearch = vi.fn()
  render(
    <SearchBar
      onSearch={onSearch}
      onClear={vi.fn()}
      isLoading={false}
      speakers={['Speaker 1', 'Speaker 2']}
    />,
  )
  await userEvent.selectOptions(screen.getByRole('combobox'), 'Speaker 1')
  await userEvent.type(screen.getByRole('textbox'), 'gradient{Enter}')
  expect(onSearch).toHaveBeenCalledWith('gradient', 'Speaker 1')
})
