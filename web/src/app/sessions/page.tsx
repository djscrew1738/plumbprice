import type { Metadata } from 'next'
import { SessionHistoryPage } from '@/components/sessions/SessionHistoryPage'

export const metadata: Metadata = {
  title: 'Chat History – PlumbPrice AI',
  description: 'Browse and resume past pricing conversations.',
}

export default function Page() {
  return <SessionHistoryPage />
}
