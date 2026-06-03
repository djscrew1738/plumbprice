import type { Metadata } from 'next'
import { Suspense } from 'react'
import { ResetPasswordForm } from '@/components/auth/ResetPasswordForm'

export const metadata: Metadata = {
  title: 'Set New Password – PlumbPrice AI',
  description: 'Set a new password for your PlumbPrice AI account.',
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={null}>
      <ResetPasswordForm />
    </Suspense>
  )
}
