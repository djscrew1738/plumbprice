'use client'

import { useState, useRef, useEffect, FormEvent, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { motion } from 'framer-motion'
import { Droplets, Eye, EyeOff } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { Button } from '@/components/ui/Button'

function LoginForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { login } = useAuth()

  const emailRef = useRef<HTMLInputElement>(null)

  const [email,    setEmail]    = useState('')
  const [password, setPassword] = useState('')
  const [showPw,   setShowPw]   = useState(false)
  const [loading,  setLoading]  = useState(false)
  const [error,    setError]    = useState<string | null>(null)
  const [touched,  setTouched]  = useState<{ email?: boolean; password?: boolean }>({})

  useEffect(() => { emailRef.current?.focus() }, [])

  const emailValid   = email.trim().length > 0 && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
  const passwordValid = password.length >= 1

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await login(email.trim(), password)
      const redirect = searchParams.get('redirect') || '/pipeline'
      router.replace(redirect)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(msg ?? 'Invalid email or password')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-dvh bg-[#060606] flex items-center justify-center p-4">
      {/* Background glow */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full blur-[120px]" style={{ background: 'radial-gradient(circle, hsl(var(--accent-hsl) / 0.15) 0%, transparent 70%)' }} />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, ease: 'easeOut' }}
        className="w-full max-w-sm"
      >
        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div className="w-14 h-14 bg-gradient-to-br from-blue-500 to-blue-700 rounded-2xl flex items-center justify-center shadow-2xl shadow-blue-600/30 mb-4">
            <Droplets size={26} className="text-white" />
          </div>
          <h1 className="text-2xl font-extrabold text-white tracking-tight">PlumbPrice AI</h1>
          <p className="text-sm text-zinc-600 mt-1">DFW Estimator — sign in to continue</p>
        </div>

        {/* Card */}
        <div className="bg-[#0f0f0f] border border-white/[0.08] rounded-2xl p-6 shadow-2xl">
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Email */}
            <div>
              <label className="block text-xs font-bold text-zinc-600 uppercase tracking-wider mb-1.5">
                Email
              </label>
              <input
                ref={emailRef}
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                onBlur={() => setTouched(t => ({ ...t, email: true }))}
                placeholder="you@company.com"
                className={`input ${error && touched.email ? 'border-[hsl(var(--danger))]' : ''} ${touched.email && emailValid ? 'ring-1 ring-emerald-500/40' : ''}`}
              />
            </div>

            {/* Password */}
            <div>
              <label className="block text-xs font-bold text-zinc-600 uppercase tracking-wider mb-1.5">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPw ? 'text' : 'password'}
                  required
                  autoComplete="current-password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  onBlur={() => setTouched(t => ({ ...t, password: true }))}
                  placeholder="••••••••"
                  className={`input pr-10 ${error && touched.password ? 'border-[hsl(var(--danger))]' : ''} ${touched.password && passwordValid ? 'ring-1 ring-emerald-500/40' : ''}`}
                />
                <button
                  type="button"
                  onClick={() => setShowPw(v => !v)}
                  aria-label="Toggle password visibility"
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-600 hover:text-zinc-300 transition-colors"
                >
                  {showPw ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            {/* Error */}
            {error && (
              <motion.p
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-xs text-[hsl(var(--danger))] bg-[hsl(var(--danger)/0.1)] border border-[hsl(var(--danger)/0.2)] rounded-xl px-3 py-2"
              >
                {error}
              </motion.p>
            )}

            {/* Submit */}
            <Button
              type="submit"
              variant="primary"
              size="md"
              isLoading={loading}
              disabled={!email || !password}
              className="w-full justify-center py-2.5 mt-2"
            >
              Sign in
            </Button>
          </form>
        </div>

        {/* Forgot password */}
        <p className="text-center mt-4">
          <a href="/forgot-password" className="text-xs text-[color:var(--accent)] hover:underline transition-colors">
            Forgot your password?
          </a>
        </p>

        <p className="text-center text-[11px] text-zinc-700 mt-5">
          PlumbPrice AI · DFW Contractors Only
        </p>
      </motion.div>
    </div>
  )
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  )
}
