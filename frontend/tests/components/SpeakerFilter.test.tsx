import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { test, expect, vi } from 'vitest'
import { SpeakerFilter } from '@/components/SpeakerFilter/SpeakerFilter'

test('not rendered when speakers list has fewer than 2 entries', () => {
  const { container } = render(
    <SpeakerFilter speakers={[]} selected={null} onChange={vi.fn()} />,
  )
  expect(container).toBeEmptyDOMElement()
})

test('not rendered when only one speaker', () => {
  render(<SpeakerFilter speakers={['Speaker 1']} selected={null} onChange={vi.fn()} />)
  expect(screen.queryByRole('combobox')).not.toBeInTheDocument()
})

test('renders All speakers option plus one per unique label', () => {
  render(
    <SpeakerFilter
      speakers={['Speaker 1', 'Speaker 2']}
      selected={null}
      onChange={vi.fn()}
    />,
  )
  expect(screen.getByRole('option', { name: 'All speakers' })).toBeInTheDocument()
  expect(screen.getByRole('option', { name: 'Speaker 1' })).toBeInTheDocument()
  expect(screen.getByRole('option', { name: 'Speaker 2' })).toBeInTheDocument()
})

test('selecting a speaker calls onChange with that label', async () => {
  const onChange = vi.fn()
  render(
    <SpeakerFilter
      speakers={['Speaker 1', 'Speaker 2']}
      selected={null}
      onChange={onChange}
    />,
  )
  await userEvent.selectOptions(screen.getByRole('combobox'), 'Speaker 1')
  expect(onChange).toHaveBeenCalledWith('Speaker 1')
})

test('selecting All speakers calls onChange with null', async () => {
  const onChange = vi.fn()
  render(
    <SpeakerFilter
      speakers={['Speaker 1', 'Speaker 2']}
      selected="Speaker 1"
      onChange={onChange}
    />,
  )
  await userEvent.selectOptions(screen.getByRole('combobox'), '')
  expect(onChange).toHaveBeenCalledWith(null)
})
