import type { Metadata } from 'next'
import { Suspense } from 'react'
import { LoginForm } from '@/components/auth/LoginForm'

export const metadata: Metadata = {
  title: 'Sign In – PlumbPrice AI',
  description: 'Sign in to PlumbPrice AI to build plumbing estimates powered by real supplier pricing.',
}

function LoginFallback() {
  return (
    <div className="p-4 space-y-3">
      <div className="mb-3 h-8 w-1/3 skeleton rounded-lg" />
      <div className="skeleton h-16 rounded-xl" />
      <div className="skeleton h-16 rounded-xl" />
    </div>
  )
}

export default function LoginPage() {
  return (
    <Suspense fallback={<LoginFallback />}>
      <LoginForm />
    </Suspense>
  )
}
