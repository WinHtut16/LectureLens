import { render, screen, act, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { test, expect } from 'vitest'
import { useAudioPlayer } from '@/lib/hooks/useAudioPlayer'

function Harness() {
  const { audioRef, currentTime, isPlaying, duration, seekTo } = useAudioPlayer()
  return (
    <div>
      <audio ref={audioRef} data-testid="audio" />
      <span data-testid="current-time">{currentTime}</span>
      <span data-testid="is-playing">{String(isPlaying)}</span>
      <span data-testid="duration">{duration}</span>
      <button onClick={() => seekTo(30)}>Seek to 30</button>
    </div>
  )
}

test('seekTo(30) sets audioRef.current.currentTime to 30', async () => {
  render(<Harness />)
  await userEvent.click(screen.getByRole('button', { name: 'Seek to 30' }))
  const audio = screen.getByTestId('audio') as HTMLAudioElement
  expect(audio.currentTime).toBe(30)
})

test('currentTime state updates when timeupdate fires', () => {
  render(<Harness />)
  const audio = screen.getByTestId('audio') as HTMLAudioElement
  Object.defineProperty(audio, 'currentTime', { value: 45, configurable: true, writable: true })
  act(() => { fireEvent(audio, new Event('timeupdate')) })
  expect(screen.getByTestId('current-time')).toHaveTextContent('45')
})

test('isPlaying becomes true on play event, false on pause', () => {
  render(<Harness />)
  const audio = screen.getByTestId('audio') as HTMLAudioElement
  expect(screen.getByTestId('is-playing')).toHaveTextContent('false')
  act(() => { fireEvent(audio, new Event('play')) })
  expect(screen.getByTestId('is-playing')).toHaveTextContent('true')
  act(() => { fireEvent(audio, new Event('pause')) })
  expect(screen.getByTestId('is-playing')).toHaveTextContent('false')
})

test('duration updates on loadedmetadata', () => {
  render(<Harness />)
  const audio = screen.getByTestId('audio') as HTMLAudioElement
  Object.defineProperty(audio, 'duration', { value: 1800, configurable: true })
  act(() => { fireEvent(audio, new Event('loadedmetadata')) })
  expect(screen.getByTestId('duration')).toHaveTextContent('1800')
})

test('audio element is NOT in state — seekTo does not trigger re-render', () => {
  let renderCount = 0
  function Counter() {
    renderCount++
    const { audioRef, seekTo } = useAudioPlayer()
    return (
      <>
        <audio ref={audioRef} />
        <button onClick={() => seekTo(10)}>Seek</button>
      </>
    )
  }
  render(<Counter />)
  const before = renderCount
  act(() => { screen.getByRole('button').click() })
  expect(renderCount).toBe(before)
})
