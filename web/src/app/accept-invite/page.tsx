import type { Metadata } from 'next'
import { Suspense } from 'react'
import { AcceptInviteForm } from '@/components/auth/AcceptInviteForm'
import { PublicLayout } from '@/components/layout/PublicLayout'

export const metadata: Metadata = {
  title: 'Accept Invitation – PlumbPrice AI',
  description: 'Accept your team invitation and join PlumbPrice AI.',
}

export default function AcceptInvitePage() {
  return (
    <Suspense fallback={null}>
      <PublicLayout
        title="Accept your invitation"
        subtitle="Set a password to create your account"
      >
        <AcceptInviteForm />
      </PublicLayout>
    </Suspense>
  )
}
