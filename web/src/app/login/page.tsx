import type { Metadata } from 'next'
import { Suspense } from 'react'
import { LoginForm } from '@/components/auth/LoginForm'
import { PublicLayout } from '@/components/layout/PublicLayout'

export const metadata: Metadata = {
  title: 'Sign In – PlumbPrice AI',
  description: 'Sign in to PlumbPrice AI to build plumbing estimates powered by real supplier pricing.',
}

function LoginFallback() {
  return (
    <PublicLayout title="PlumbPrice AI" subtitle="DFW Estimator — sign in to continue">
      <div className="space-y-4">
        <div className="skeleton h-16 rounded-xl" />
        <div className="skeleton h-16 rounded-xl" />
        <div className="skeleton h-10 rounded-xl" />
      </div>
    </PublicLayout>
  )
}

export default function LoginPage() {
  return (
    <Suspense fallback={<LoginFallback />}>
      <PublicLayout
        title="PlumbPrice AI"
        subtitle="DFW Estimator — sign in to continue"
      >
        <LoginForm />
      </PublicLayout>
    </Suspense>
  )
}
