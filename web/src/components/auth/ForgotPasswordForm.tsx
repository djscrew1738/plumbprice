'use client'

import { useState, useRef, useEffect, FormEvent } from 'react'
import { motion } from 'framer-motion'
import { api } from '@/lib/api'
import { Input } from '@/components/ui/Input'
import { FormLayout } from '@/components/ui/FormLayout'

export function ForgotPasswordForm() {
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

  if (submitted) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="space-y-3"
      >
        <div className="rounded-lg border border-[hsl(var(--success)/0.2)] bg-[hsl(var(--success)/0.1)] p-4 text-sm text-[hsl(var(--success))]">
          ✓ Check your email for a reset link. It expires in 1 hour.
        </div>
        <p className="text-xs text-[color:var(--muted-ink)]">
          Didn&apos;t get it? Check your spam folder or try again in an hour.
        </p>
      </motion.div>
    )
  }

  return (
    <FormLayout
      onSubmit={handleSubmit}
      error={error}
      isSubmitting={loading}
      submitLabel="Send reset link"
      submitButtonClassName="w-full justify-center py-2.5"
      className="space-y-4"
    >
      <Input
        id="email"
        ref={emailRef}
        type="email"
        label="Email"
        placeholder="you@company.com"
        autoComplete="email"
        required
        value={email}
        onChange={e => setEmail(e.target.value)}
      />
    </FormLayout>
  )
}
