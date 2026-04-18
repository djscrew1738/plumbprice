'use client'

import { useState, useRef, useEffect, FormEvent, Suspense } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { motion } from 'framer-motion'
import { Droplets, Eye, EyeOff, ArrowLeft } from 'lucide-react'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/Button'

interface AcceptInviteResponse {
  access_token: string
  token_type: string
  user: {
    id: number
    email: string
    full_name: string
    role: string
    is_admin: boolean
  }
}

function AcceptInviteForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const token = searchParams.get('token') ?? ''

  const pwRef = useRef<HTMLInputElement>(null)
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [fullName, setFullName] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    pwRef.current?.focus()
  }, [])

  const canSubmit =
    Boolean(token) && password.length >= 8 && confirm === password && !loading

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!token) {
      setError('Missing invite token. Use the link from your invitation email.')
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
      const { data } = await api.post<AcceptInviteResponse>('/auth/accept-invite', {
        token,
        password,
        full_name: fullName || undefined,
      })
      try {
        localStorage.setItem('pp_token', data.access_token)
        localStorage.setItem('pp_user', JSON.stringify(data.user))
      } catch {
        // ignore storage errors
      }
      router.push('/')
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(msg ?? 'Could not accept invitation. The link may have expired.')
    } finally {
      setLoading(false)
    }
  }

  if (!token) {
    return (
      <div className="min-h-dvh bg-[#060606] flex items-center justify-center p-4">
        <div className="w-full max-w-sm rounded-2xl border border-white/[0.08] bg-[#0f0f0f] p-6 text-center">
          <h1 className="text-lg font-semibold text-white">Missing invite token</h1>
          <p className="mt-2 text-sm text-zinc-400">
            Use the link from your invitation email to accept.
          </p>
          <Link href="/login" className="mt-4 inline-flex items-center gap-1 text-sm text-blue-400 hover:underline">
            <ArrowLeft size={14} /> Back to login
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-dvh bg-[#060606] flex items-center justify-center p-4">
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
          <h1 className="text-2xl font-extrabold text-white tracking-tight">
            Accept your invitation
          </h1>
          <p className="text-sm text-zinc-500 mt-1">Set a password to create your account</p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="bg-[#0f0f0f] border border-white/[0.08] rounded-2xl p-6 shadow-2xl space-y-4"
        >
          <div>
            <label className="block text-xs font-medium text-zinc-400 mb-1" htmlFor="full_name">
              Full name (optional)
            </label>
            <input
              id="full_name"
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="w-full rounded-lg border border-white/10 bg-black/40 px-3 py-2 text-sm text-white placeholder:text-zinc-600 focus:border-blue-500 focus:outline-none"
              placeholder="Jane Doe"
              autoComplete="name"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-zinc-400 mb-1" htmlFor="password">
              Password
            </label>
            <div className="relative">
              <input
                id="password"
                ref={pwRef}
                type={showPw ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-lg border border-white/10 bg-black/40 px-3 py-2 pr-9 text-sm text-white placeholder:text-zinc-600 focus:border-blue-500 focus:outline-none"
                placeholder="At least 8 characters"
                autoComplete="new-password"
                minLength={8}
                required
              />
              <button
                type="button"
                onClick={() => setShowPw((v) => !v)}
                className="absolute inset-y-0 right-2 flex items-center text-zinc-500 hover:text-zinc-300"
                aria-label={showPw ? 'Hide password' : 'Show password'}
              >
                {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-zinc-400 mb-1" htmlFor="confirm">
              Confirm password
            </label>
            <input
              id="confirm"
              type={showPw ? 'text' : 'password'}
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              className="w-full rounded-lg border border-white/10 bg-black/40 px-3 py-2 text-sm text-white placeholder:text-zinc-600 focus:border-blue-500 focus:outline-none"
              autoComplete="new-password"
              minLength={8}
              required
            />
          </div>

          {error && (
            <p className="text-sm text-red-400" role="alert">
              {error}
            </p>
          )}

          <Button type="submit" className="w-full" isLoading={loading} disabled={!canSubmit}>
            Accept invitation
          </Button>

          <p className="pt-2 text-center text-xs text-zinc-500">
            Already have an account?{' '}
            <Link href="/login" className="text-blue-400 hover:underline">
              Sign in
            </Link>
          </p>
        </form>
      </motion.div>
    </div>
  )
}

export default function AcceptInvitePage() {
  return (
    <Suspense fallback={null}>
      <AcceptInviteForm />
    </Suspense>
  )
}
