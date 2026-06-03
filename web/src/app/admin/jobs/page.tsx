import type { Metadata } from 'next'
import { JobsPage } from '@/components/admin/JobsPage'

export const metadata: Metadata = {
  title: 'Failed Jobs – PlumbPrice AI',
  description: 'Worker observability and retry management.',
}

export default function AdminJobs() {
  return <JobsPage />
}
