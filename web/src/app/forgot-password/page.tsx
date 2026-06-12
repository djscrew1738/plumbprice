import type { Metadata } from 'next'
import Link from 'next/link'
import { ArrowLeft } from 'lucide-react'
import { ForgotPasswordForm } from '@/components/auth/ForgotPasswordForm'
import { PublicLayout } from '@/components/layout/PublicLayout'

export const metadata: Metadata = {
  title: 'Reset Password – PlumbPrice AI',
  description: 'Request a password reset for your PlumbPrice AI account.',
}

export default function ForgotPasswordPage() {
  return (
    <PublicLayout
      title="Reset password"
      subtitle="We&apos;ll send a link to your inbox"
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
      <ForgotPasswordForm />
    </PublicLayout>
  )
}
