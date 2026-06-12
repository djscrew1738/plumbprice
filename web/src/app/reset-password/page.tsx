import type { Metadata } from 'next'
import { Suspense } from 'react'
import Link from 'next/link'
import { ArrowLeft } from 'lucide-react'
import { ResetPasswordForm } from '@/components/auth/ResetPasswordForm'
import { PublicLayout } from '@/components/layout/PublicLayout'

export const metadata: Metadata = {
  title: 'Set New Password – PlumbPrice AI',
  description: 'Set a new password for your PlumbPrice AI account.',
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={null}>
      <PublicLayout
        title="Choose a new password"
        subtitle="At least 8 characters"
        footer={
          <p className="mt-4 text-center">
            <Link
              href="/login"
              className="inline-flex items-center gap-1 text-xs text-[color:var(--accent)] hover:underline transition-colors"
            >
              <ArrowLeft size={12} /> Back to sign in
            </Link>
          </p>
        }
      >
        <ResetPasswordForm />
      </PublicLayout>
    </Suspense>
  )
}
