'use client'

import { useState, useRef, useEffect, FormEvent } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { Eye, EyeOff, ArrowLeft } from 'lucide-react'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { FormLayout } from '@/components/ui/FormLayout'

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

export function AcceptInviteForm() {
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
      if (!data.user) setError('Could not complete sign in.')
      router.push('/')
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(msg ?? 'Could not accept invitation. The link may have expired.')
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

  if (!token) {
    return (
      <div className="space-y-3 text-center">
        <h2 className="text-lg font-semibold text-[color:var(--ink)]">Missing invite token</h2>
        <p className="text-sm text-[color:var(--muted-ink)]">
          Use the link from your invitation email to accept.
        </p>
        <Link
          href="/login"
          className="inline-flex items-center gap-1 text-sm text-[color:var(--accent)] hover:underline"
        >
          <ArrowLeft size={14} /> Back to login
        </Link>
      </div>
    )
  }

  return (
    <FormLayout
      onSubmit={handleSubmit}
      error={error}
      isSubmitting={loading}
      submitLabel="Accept invitation"
      submitButtonClassName="w-full justify-center py-2.5"
      className="space-y-4"
      footer={
        <p className="text-center text-xs text-[color:var(--muted-ink)]">
          Already have an account?{' '}
          <Link href="/login" className="text-[color:var(--accent)] hover:underline">
            Sign in
          </Link>
        </p>
      }
    >
      <Input
        id="full_name"
        type="text"
        label="Full name (optional)"
        placeholder="Jane Doe"
        autoComplete="name"
        value={fullName}
        onChange={e => setFullName(e.target.value)}
      />

      <Input
        id="password"
        ref={pwRef}
        type={showPw ? 'text' : 'password'}
        label="Password"
        placeholder="At least 8 characters"
        autoComplete="new-password"
        minLength={8}
        required
        value={password}
        onChange={e => setPassword(e.target.value)}
        rightAction={PasswordToggle}
      />

      <Input
        id="confirm"
        type={showPw ? 'text' : 'password'}
        label="Confirm password"
        autoComplete="new-password"
        minLength={8}
        required
        value={confirm}
        onChange={e => setConfirm(e.target.value)}
        error={confirm.length > 0 && confirm !== password ? 'Passwords do not match' : undefined}
      />
    </FormLayout>
  )
}
