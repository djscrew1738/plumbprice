import type { Metadata } from 'next'
import { Suspense } from 'react'
import { EstimatesListPage } from '@/components/estimates/EstimatesListPage'

export const metadata: Metadata = {
  title: 'Saved Estimates – PlumbPrice AI',
  description: 'Resume and review recent pricing work.',
}

export default function Estimates() {
  return (
    <Suspense>
      <EstimatesListPage />
    </Suspense>
  )
}
