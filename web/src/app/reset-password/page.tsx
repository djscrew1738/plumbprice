'use client'

import { useState, useRef, useEffect, FormEvent, Suspense } from 'react'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { motion } from 'framer-motion'
import { Droplets, Eye, EyeOff, ArrowLeft } from 'lucide-react'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/Button'

function ResetPasswordForm() {
  const searchParams = useSearchParams()
  const token = searchParams.get('token') ?? ''

  const pwRef = useRef<HTMLInputElement>(null)
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => { pwRef.current?.focus() }, [])

  const tooShort = password.length > 0 && password.length < 8
  const mismatch = confirm.length > 0 && confirm !== password
  const canSubmit = token && password.length >= 8 && confirm === password && !loading

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!token) {
      setError('Missing reset token. Please use the link from your email.')
      return
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters.')
      return
    }
    if (password !== confirm) {
      setError('Passwords do not match.')
      return
    }

    setLoading(true)
    try {
      await api.post('/auth/reset-password', { token, new_password: password })
      setSuccess(true)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(msg ?? 'Could not reset password. The link may have expired.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-dvh bg-[#060606] flex items-center justify-center p-4">
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full blur-[120px]" style={{ background: 'radial-gradient(circle, hsl(var(--accent-hsl) / 0.15) 0%, transparent 70%)' }} />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, ease: 'easeOut' }}
        className="w-full max-w-sm"
      >
        <div className="flex flex-col items-center mb-8">
          <div className="w-14 h-14 bg-gradient-to-br from-blue-500 to-blue-700 rounded-2xl flex items-center justify-center shadow-2xl shadow-blue-600/30 mb-4">
            <Droplets size={26} className="text-white" />
          </div>
          <h1 className="text-2xl font-extrabold text-white tracking-tight">Choose a new password</h1>
          <p className="text-sm text-zinc-600 mt-1">At least 8 characters</p>
        </div>

        <div className="bg-[#0f0f0f] border border-white/[0.08] rounded-2xl p-6 shadow-2xl">
          {success ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="space-y-4"
            >
              <p className="text-sm text-emerald-400 font-semibold">Password updated.</p>
              <p className="text-xs text-zinc-500">You can now sign in with your new password.</p>
              <Link
                href="/login"
                className="block w-full text-center py-2.5 rounded-xl bg-gradient-to-br from-blue-500 to-blue-700 text-white text-sm font-semibold hover:from-blue-400 hover:to-blue-600 transition-colors"
              >
                Go to sign in
              </Link>
            </motion.div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label htmlFor="password" className="block text-xs font-bold text-zinc-600 uppercase tracking-wider mb-1.5">
                  New password
                </label>
                <div className="relative">
                  <input
                    id="password"
                    ref={pwRef}
                    type={showPw ? 'text' : 'password'}
                    required
                    minLength={8}
                    autoComplete="new-password"
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className={`input pr-10 ${tooShort ? 'border-[hsl(var(--danger))]' : ''}`}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPw(v => !v)}
                    aria-label={showPw ? 'Hide password' : 'Show password'}
                    className="absolute right-2 top-1/2 -translate-y-1/2 flex min-h-[36px] min-w-[36px] items-center justify-center rounded-lg text-zinc-600 hover:text-zinc-300 transition-colors"
                  >
                    {showPw ? <EyeOff size={15} /> : <Eye size={15} />}
                  </button>
                </div>
                {tooShort && (
                  <p className="text-[11px] text-[hsl(var(--danger))] mt-1">At least 8 characters</p>
                )}
              </div>

              <div>
                <label htmlFor="confirm" className="block text-xs font-bold text-zinc-600 uppercase tracking-wider mb-1.5">
                  Confirm password
                </label>
                <input
                  id="confirm"
                  type={showPw ? 'text' : 'password'}
                  required
                  minLength={8}
                  autoComplete="new-password"
                  value={confirm}
                  onChange={e => setConfirm(e.target.value)}
                  placeholder="••••••••"
                  className={`input ${mismatch ? 'border-[hsl(var(--danger))]' : ''}`}
                />
                {mismatch && (
                  <p className="text-[11px] text-[hsl(var(--danger))] mt-1">Passwords do not match</p>
                )}
              </div>

              {error && (
                <motion.p
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="text-xs text-[hsl(var(--danger))] bg-[hsl(var(--danger)/0.1)] border border-[hsl(var(--danger)/0.2)] rounded-xl px-3 py-2"
                >
                  {error}
                </motion.p>
              )}

              <Button
                type="submit"
                variant="primary"
                size="md"
                isLoading={loading}
                disabled={!canSubmit}
                className="w-full justify-center py-2.5 mt-2"
              >
                Update password
              </Button>
            </form>
          )}
        </div>

        <p className="text-center mt-4">
          <Link href="/login" className="inline-flex items-center gap-1 text-xs text-[color:var(--accent)] hover:underline transition-colors">
            <ArrowLeft size={12} /> Back to sign in
          </Link>
        </p>
      </motion.div>
    </div>
  )
}

export default function ResetPasswordPage() {
  return (
    <Suspense>
      <ResetPasswordForm />
    </Suspense>
  )
}
