'use client'

import { useState, useRef, useEffect, FormEvent } from 'react'
import Link from 'next/link'
import { motion } from 'framer-motion'
import { Droplets, ArrowLeft } from 'lucide-react'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/Button'

export default function ForgotPasswordPage() {
  const emailRef = useRef<HTMLInputElement>(null)
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => { emailRef.current?.focus() }, [])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await api.post('/auth/forgot-password', { email: email.trim() })
      setSubmitted(true)
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status
      if (status === 429) {
        setError('Too many password reset requests. Try again in 1 hour.')
      } else {
        const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        setError(msg ?? 'Something went wrong. Please try again.')
      }
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
          <h1 className="text-2xl font-extrabold text-white tracking-tight">Reset password</h1>
          <p className="text-sm text-zinc-600 mt-1">We&apos;ll send a link to your inbox</p>
        </div>

        <div className="bg-[#0f0f0f] border border-white/[0.08] rounded-2xl p-6 shadow-2xl">
          {submitted ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="space-y-3"
            >
              <div className="rounded-lg bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 p-4 text-sm text-emerald-800 dark:text-emerald-300">
                ✓ Check your email for a reset link. It expires in 1 hour.
              </div>
              <p className="text-xs text-zinc-600">
                Didn&apos;t get it? Check your spam folder or try again in an hour.
              </p>
            </motion.div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label htmlFor="email" className="block text-xs font-bold text-zinc-600 uppercase tracking-wider mb-1.5">
                  Email
                </label>
                <input
                  id="email"
                  ref={emailRef}
                  type="email"
                  required
                  autoComplete="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="you@company.com"
                  className="input"
                />
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
                disabled={!email}
                className="w-full justify-center py-2.5 mt-2"
              >
                Send reset link
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
