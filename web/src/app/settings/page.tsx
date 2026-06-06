import type { Metadata } from 'next'
import { SettingsLayout } from '@/components/settings/SettingsLayout'

export const metadata: Metadata = {
  title: 'Settings – PlumbPrice AI',
  description: 'Manage your account, organization, and preferences.',
}

export default function SettingsPage() {
  return <SettingsLayout />
}
