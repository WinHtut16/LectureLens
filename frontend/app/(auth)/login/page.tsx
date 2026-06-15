'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { login, ApiError } from '@/lib/api'
import { useAuth } from '@/components/auth/AuthProvider'

function LensLogo() {
  return (
    <div className="flex items-center gap-2.5">
      <svg width="26" height="26" viewBox="0 0 26 26" fill="none">
        <circle cx="13" cy="13" r="11.25" stroke="#6e8cff" strokeWidth="1.5" />
        <circle cx="13" cy="13" r="6" stroke="#6e8cff" strokeWidth="1.5" opacity="0.55" />
        <circle cx="13" cy="13" r="2.4" fill="#6e8cff" />
      </svg>
      <span className="text-sm font-medium text-text tracking-wide">LectureLens</span>
    </div>
  )
}

export default function LoginPage() {
  const router = useRouter()
  const { login: setAuth } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const { token, user } = await login(email, password)
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
    <div className="min-h-screen grid grid-cols-1 md:grid-cols-2">
      {/* Left — form column */}
      <div className="flex flex-col justify-center px-8 py-12 md:px-16">
        <div className="max-w-sm w-full mx-auto space-y-8">
          <LensLogo />

          <div>
            <h1 className="font-serif text-[2.25rem] leading-tight text-text">Welcome back</h1>
            <p className="text-sm text-text-muted mt-1">Sign in to continue searching</p>
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
                Password
              </label>
              <input
                id="password"
                type="password"
                required
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className={inputClass}
              />
            </div>

            {error && (
              <p role="alert" className="text-xs text-danger">{error}</p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-primary-fill hover:bg-primary active:bg-primary-press text-white rounded-md py-2.5 text-sm font-medium disabled:opacity-50 transition-colors mt-2"
            >
              {loading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>

          <p className="text-sm text-text-muted">
            No account?{' '}
            <Link href="/signup" className="text-primary hover:text-primary-hover underline-offset-4 hover:underline">
              Create one
            </Link>
          </p>
        </div>
      </div>

      {/* Right — editorial dark panel (hidden on mobile) */}
      <div className="hidden md:flex flex-col justify-center px-16 bg-surface border-l border-border relative overflow-hidden">
        <div className="absolute -right-32 -top-32 w-[500px] h-[500px] rounded-full border border-primary/10" />
        <div className="absolute -right-16 -top-16 w-[360px] h-[360px] rounded-full border border-primary/[.06]" />
        <div className="absolute right-8 top-8 w-[220px] h-[220px] rounded-full border border-primary/[.04]" />

        <div className="relative max-w-xs space-y-6">
          <p className="font-serif text-[1.6rem] leading-snug text-text">
            {"\"Where did the professor explain "}
            <mark className="bg-[rgba(242,193,78,.28)] text-[#fbe4a6] not-italic px-0.5 rounded-sm">
              backpropagation
            </mark>
            {"?\""}
          </p>
          <p className="text-sm text-text-muted leading-relaxed">
            Type a question. Jump to the exact second. No scrubbing required.
          </p>
          <div className="flex items-center gap-2 text-xs text-text-faint font-mono">
            <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse" />
            Semantic search · Speaker-aware · Timestamped
          </div>
        </div>
      </div>
    </div>
  )
}
