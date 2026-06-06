import type { Metadata } from 'next'
import { ForgotPasswordForm } from '@/components/auth/ForgotPasswordForm'

export const metadata: Metadata = {
  title: 'Reset Password – PlumbPrice AI',
  description: 'Request a password reset for your PlumbPrice AI account.',
}

export default function ForgotPasswordPage() {
  return <ForgotPasswordForm />
}
