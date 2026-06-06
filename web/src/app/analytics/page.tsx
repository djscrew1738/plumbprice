import type { Metadata } from 'next'
import { AnalyticsPage } from '@/components/analytics/AnalyticsPage'

export const metadata: Metadata = {
  title: 'Analytics – PlumbPrice AI',
  description: 'Outcome insights and performance trends for your plumbing estimates.',
}

export default function Page() {
  return <AnalyticsPage />
}
