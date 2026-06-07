'use client'

import { useState, useRef, useEffect, FormEvent } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { Droplets, Eye, EyeOff, UserCircle } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { Button } from '@/components/ui/Button'
import { BrandFooter } from '@/components/layout/BrandFooter'

export function LoginForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { login, loginAsGuest } = useAuth()

  // Uncontrolled inputs — no state update on every keystroke, so React
  // doesn't reconcile on each character. Values are read only on submit/blur.
  const emailRef    = useRef<HTMLInputElement>(null)
  const passwordRef = useRef<HTMLInputElement>(null)

  const [showPw,   setShowPw]   = useState(false)
  const [loading,  setLoading]  = useState(false)
  const [guestLoading, setGuestLoading] = useState(false)
  const [error,    setError]    = useState<string | null>(null)

  // Inline validation feedback — only updated on blur, not on every keystroke.
  const [emailState,    setEmailState]    = useState<'idle' | 'valid' | 'invalid'>('idle')
  const [passwordState, setPasswordState] = useState<'idle' | 'valid'>('idle')

  useEffect(() => { emailRef.current?.focus() }, [])

  const validateEmail = (v: string) =>
    v.trim().length > 0 && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v.trim())

  const handleEmailBlur = () => {
    const v = emailRef.current?.value ?? ''
    setEmailState(validateEmail(v) ? 'valid' : v.length > 0 ? 'invalid' : 'idle')
  }

  const handlePasswordBlur = () => {
    const v = passwordRef.current?.value ?? ''
    setPasswordState(v.length > 0 ? 'valid' : 'idle')
  }

  const redirectAfterLogin = () => {
    const redirect = searchParams.get('redirect') || '/'
    router.replace(redirect)
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    const email    = emailRef.current?.value ?? ''
    const password = passwordRef.current?.value ?? ''
    if (!email || !password) return
    setError(null)
    setLoading(true)
    try {
      await login(email.trim(), password)
      redirectAfterLogin()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(msg ?? 'Invalid email or password')
    } finally {
      setLoading(false)
    }
  }

  const handleGuestLogin = async () => {
    setError(null)
    setGuestLoading(true)
    try {
      await loginAsGuest()
      redirectAfterLogin()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(msg ?? 'Unable to start guest session. Please try again.')
    } finally {
      setGuestLoading(false)
    }
  }

  const emailCls = [
    'input',
    emailState === 'invalid' ? 'border-[hsl(var(--danger))]' : '',
    emailState === 'valid'   ? 'ring-1 ring-emerald-500/40'  : '',
  ].filter(Boolean).join(' ')

  const passwordCls = [
    'input pr-10',
    passwordState === 'valid' ? 'ring-1 ring-emerald-500/40' : '',
  ].filter(Boolean).join(' ')

  return (
    <div className="min-h-dvh bg-[#060606] flex items-center justify-center p-4">
      {/* Background glow — fixed so it never re-renders with form state */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden" aria-hidden="true">
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full blur-[120px] bg-[radial-gradient(circle,hsl(24_78%_52%_/_0.15)_0%,transparent_70%)]" />
      </div>

      {/* CSS-animated wrapper — no JS animation overhead per re-render */}
      <div className="login-card-entry w-full max-w-sm">
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
              <label htmlFor="email" className="block text-xs font-bold text-zinc-600 uppercase tracking-wider mb-1.5">
                Email
              </label>
              <input
                id="email"
                ref={emailRef}
                type="email"
                required
                autoComplete="email"
                defaultValue=""
                onBlur={handleEmailBlur}
                placeholder="you@company.com"
                className={emailCls}
              />
            </div>

            {/* Password */}
            <div>
              <label htmlFor="password" className="block text-xs font-bold text-zinc-600 uppercase tracking-wider mb-1.5">
                Password
              </label>
              <div className="relative">
                <input
                  id="password"
                  ref={passwordRef}
                  type={showPw ? 'text' : 'password'}
                  required
                  autoComplete="current-password"
                  defaultValue=""
                  onBlur={handlePasswordBlur}
                  placeholder="••••••••"
                  className={passwordCls}
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
            </div>

            {/* Error */}
            {error && (
              <p className="text-xs text-[hsl(var(--danger))] bg-[hsl(var(--danger)/0.1)] border border-[hsl(var(--danger)/0.2)] rounded-xl px-3 py-2">
                {error}
              </p>
            )}

            {/* Submit */}
            <Button
              type="submit"
              variant="primary"
              size="md"
              isLoading={loading}
              className="w-full justify-center py-2.5 mt-2"
            >
              Sign in
            </Button>

            <div className="relative py-1">
              <div className="absolute inset-0 flex items-center">
                <span className="w-full border-t border-white/[0.08]" />
              </div>
              <div className="relative flex justify-center">
                <span className="bg-[#0f0f0f] px-2 text-[10px] font-medium uppercase tracking-wider text-zinc-600">
                  or
                </span>
              </div>
            </div>

            <Button
              type="button"
              variant="secondary"
              size="md"
              isLoading={guestLoading}
              onClick={handleGuestLogin}
              className="w-full justify-center py-2.5"
            >
              <UserCircle size={18} aria-hidden="true" />
              Continue as Guest
            </Button>
          </form>
        </div>

        {/* Forgot password */}
        <p className="text-center mt-4">
          <Link href="/forgot-password" className="text-xs text-[color:var(--accent)] hover:underline transition-colors">
            Forgot your password?
          </Link>
        </p>

        <BrandFooter className="mt-5" />
      </div>
    </div>
  )
}
