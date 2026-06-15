'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { signup, ApiError } from '@/lib/api'
import { useAuth } from '@/components/auth/AuthProvider'

export default function SignupPage() {
  const router = useRouter()
  const { login: setAuth } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    if (password.length < 10) {
      setError('Password must be at least 10 characters.')
      return
    }
    setLoading(true)
    try {
      const { token, user } = await signup(email, password)
      setAuth(token, user)
      router.push('/recordings')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const inputClass =
    'w-full bg-surface-2 border border-border rounded-md px-3 py-2 text-sm text-text placeholder:text-text-faint focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary'

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-bg px-4">
      <div className="w-full max-w-sm space-y-8">
        {/* Logo */}
        <div className="flex items-center gap-2.5">
          <svg width="26" height="26" viewBox="0 0 26 26" fill="none">
            <circle cx="13" cy="13" r="11.25" stroke="#6e8cff" strokeWidth="1.5" />
            <circle cx="13" cy="13" r="6" stroke="#6e8cff" strokeWidth="1.5" opacity="0.55" />
            <circle cx="13" cy="13" r="2.4" fill="#6e8cff" />
          </svg>
          <span className="text-sm font-medium text-text tracking-wide">LectureLens</span>
        </div>

        <div>
          <h1 className="font-serif text-[2.25rem] leading-tight text-text">Create account</h1>
          <p className="text-sm text-text-muted mt-1">Start searching your recordings</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <label htmlFor="email" className="text-xs font-medium text-text-muted uppercase tracking-wider">
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={inputClass}
              placeholder="you@university.edu"
            />
          </div>

          <div className="space-y-1.5">
            <label htmlFor="password" className="text-xs font-medium text-text-muted uppercase tracking-wider">
              Password <span className="text-text-faint normal-case">(min 10 chars)</span>
            </label>
            <input
              id="password"
              type="password"
              required
              minLength={10}
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={inputClass}
            />
          </div>

          {error && <p role="alert" className="text-xs text-danger">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-primary-fill hover:bg-primary active:bg-primary-press text-white rounded-md py-2.5 text-sm font-medium disabled:opacity-50 transition-colors mt-2"
          >
            {loading ? 'Creating account…' : 'Create account'}
          </button>
        </form>

        <p className="text-sm text-text-muted text-center">
          Already have an account?{' '}
          <Link href="/login" className="text-primary hover:text-primary-hover underline-offset-4 hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  )
}
