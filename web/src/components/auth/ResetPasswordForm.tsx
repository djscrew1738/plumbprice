'use client'

import { useState, useRef, useEffect, FormEvent } from 'react'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { motion } from 'framer-motion'
import { Eye, EyeOff } from 'lucide-react'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { FormLayout } from '@/components/ui/FormLayout'

export function ResetPasswordForm() {
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

  const PasswordToggle = (
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
  )

  if (success) {
    return (
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4">
        <p className="text-sm font-semibold text-[hsl(var(--success))]">Password updated.</p>
        <p className="text-xs text-[color:var(--muted-ink)]">
          You can now sign in with your new password.
        </p>
        <Link
          href="/login"
          className="block w-full rounded-xl bg-gradient-to-br from-[color:var(--accent)] to-[color:var(--accent-strong)] py-2.5 text-center text-sm font-semibold text-[color:var(--ink-inverse)] transition-all hover:brightness-110"
        >
          Go to sign in
        </Link>
      </motion.div>
    )
  }

  return (
    <FormLayout
      onSubmit={handleSubmit}
      error={error}
      isSubmitting={loading}
      submitLabel="Update password"
      submitButtonClassName="w-full justify-center py-2.5"
      className="space-y-4"
    >
      <Input
        id="password"
        ref={pwRef}
        type={showPw ? 'text' : 'password'}
        label="New password"
        placeholder="••••••••"
        autoComplete="new-password"
        minLength={8}
        required
        value={password}
        onChange={e => setPassword(e.target.value)}
        error={tooShort ? 'At least 8 characters' : undefined}
        rightAction={PasswordToggle}
      />

      <Input
        id="confirm"
        type={showPw ? 'text' : 'password'}
        label="Confirm password"
        placeholder="••••••••"
        autoComplete="new-password"
        minLength={8}
        required
        value={confirm}
        onChange={e => setConfirm(e.target.value)}
        error={mismatch ? 'Passwords do not match' : undefined}
      />
    </FormLayout>
  )
}
