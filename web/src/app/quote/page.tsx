import type { Metadata } from 'next'
import { PublicQuotePage } from '@/components/quote/PublicQuotePage'

export const metadata: Metadata = {
  title: 'Quick Quote – PlumbPrice AI',
  description: 'Get a fast plumbing estimate powered by real supplier pricing.',
}

export default function QuotePage() {
  return <PublicQuotePage />
}
