import type { Metadata } from 'next'
import { AdminUsersPage } from '@/components/admin/UsersPage'

export const metadata: Metadata = {
  title: 'Team – PlumbPrice AI',
  description: 'Manage users, roles, and invitations.',
}

export default function Page() {
  return <AdminUsersPage />
}
