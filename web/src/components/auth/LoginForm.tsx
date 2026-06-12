'use client'

import { useState, useRef, useEffect, FormEvent } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { Eye, EyeOff, UserCircle } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { FormLayout } from '@/components/ui/FormLayout'

export function LoginForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { login, loginAsGuest } = useAuth()

  // Uncontrolled inputs avoid React reconciliation on every keystroke.
  const emailRef = useRef<HTMLInputElement>(null)
  const passwordRef = useRef<HTMLInputElement>(null)

  const [showPw, setShowPw] = useState(false)
  const [loading, setLoading] = useState(false)
  const [guestLoading, setGuestLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Inline validation feedback updated only on blur.
  const [emailState, setEmailState] = useState<'idle' | 'valid' | 'invalid'>('idle')
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
    const email = emailRef.current?.value ?? ''
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

  return (
    <FormLayout
      onSubmit={handleSubmit}
      error={error}
      isSubmitting={loading}
      submitLabel="Sign in"
      submitButtonClassName="w-full justify-center py-2.5"
      className="space-y-4"
      secondaryAction={
        <Link
          href="/forgot-password"
          className="text-xs text-[color:var(--accent)] hover:underline transition-colors"
        >
          Forgot your password?
        </Link>
      }
    >
      <Input
        id="email"
        ref={emailRef}
        type="email"
        label="Email"
        placeholder="you@company.com"
        autoComplete="email"
        defaultValue=""
        onBlur={handleEmailBlur}
        error={emailState === 'invalid' ? 'Please enter a valid email address.' : undefined}
        className={emailState === 'valid' ? 'ring-1 ring-emerald-500/40' : ''}
      />

      <Input
        id="password"
        ref={passwordRef}
        type={showPw ? 'text' : 'password'}
        label="Password"
        placeholder="••••••••"
        autoComplete="current-password"
        defaultValue=""
        onBlur={handlePasswordBlur}
        className={passwordState === 'valid' ? 'ring-1 ring-emerald-500/40' : ''}
        rightAction={
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={() => setShowPw(v => !v)}
            aria-label={showPw ? 'Hide password' : 'Show password'}
            className="h-8 w-8"
          >
            {showPw ? <EyeOff size={15} /> : <Eye size={15} />}
          </Button>
        }
      />

      <div className="relative py-1">
        <div className="absolute inset-0 flex items-center">
          <span className="w-full border-t border-[color:var(--line)]" />
        </div>
        <div className="relative flex justify-center">
          <span className="bg-[color:var(--panel-solid)] px-2 text-[10px] font-medium uppercase tracking-wider text-[color:var(--muted-ink)]">
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
    </FormLayout>
  )
}
