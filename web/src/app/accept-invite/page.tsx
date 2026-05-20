import { Suspense } from 'react'
import { AcceptInviteForm } from '@/components/auth/AcceptInviteForm'

export default function AcceptInvitePage() {
  return (
    <Suspense fallback={null}>
      <AcceptInviteForm />
    </Suspense>
  )
}
