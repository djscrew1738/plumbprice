import type { Metadata } from 'next'
import { ProposalsPage } from '@/components/proposals/ProposalsPage'

export const metadata: Metadata = {
  title: 'Proposals – PlumbPrice AI',
  description: 'Customer-ready bid outputs and proposal tracking.',
}

export default function Page() {
  return <ProposalsPage />
}
