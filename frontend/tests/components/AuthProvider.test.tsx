import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, test, expect, vi } from 'vitest'
import { AuthProvider, useAuth } from '@/components/auth/AuthProvider'

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

function AuthConsumer() {
  const { token, user, login, logout } = useAuth()
  return (
    <div>
      <span data-testid="token">{token ?? 'null'}</span>
      <span data-testid="email">{user?.email ?? 'none'}</span>
      <button
        onClick={() =>
          login('test-jwt', { id: '1', email: 'a@b.com', created_at: '2026-01-01' })
        }
      >
        Login
      </button>
      <button onClick={logout}>Logout</button>
    </div>
  )
}

test('token is null initially', () => {
  render(<AuthProvider><AuthConsumer /></AuthProvider>)
  expect(screen.getByTestId('token')).toHaveTextContent('null')
})

test('login() sets token and user in memory', async () => {
  render(<AuthProvider><AuthConsumer /></AuthProvider>)
  await userEvent.click(screen.getByRole('button', { name: 'Login' }))
  expect(screen.getByTestId('token')).toHaveTextContent('test-jwt')
  expect(screen.getByTestId('email')).toHaveTextContent('a@b.com')
})

test('token is NEVER written to localStorage', async () => {
  const spy = vi.spyOn(Storage.prototype, 'setItem')
  render(<AuthProvider><AuthConsumer /></AuthProvider>)
  await userEvent.click(screen.getByRole('button', { name: 'Login' }))
  expect(spy).not.toHaveBeenCalled()
  spy.mockRestore()
})

test('logout() clears token and user', async () => {
  render(<AuthProvider><AuthConsumer /></AuthProvider>)
  await userEvent.click(screen.getByRole('button', { name: 'Login' }))
  await userEvent.click(screen.getByRole('button', { name: 'Logout' }))
  expect(screen.getByTestId('token')).toHaveTextContent('null')
  expect(screen.getByTestId('email')).toHaveTextContent('none')
})

test('useAuth throws when used outside AuthProvider', () => {
  const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
  expect(() => render(<AuthConsumer />)).toThrow('useAuth must be used within AuthProvider')
  spy.mockRestore()
})
