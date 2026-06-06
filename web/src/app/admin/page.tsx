import type { Metadata } from 'next'
import { AdminPage } from '@/components/admin/AdminPage'

export const metadata: Metadata = {
  title: 'Admin – PlumbPrice AI',
  description: 'Manage pricing rules, templates, and system settings.',
}

export default function Admin() {
  return <AdminPage />
}
