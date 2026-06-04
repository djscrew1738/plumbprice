import type { Metadata } from 'next'
import { Suspense } from 'react'
import { EstimatesListPage } from '@/components/estimates/EstimatesListPage'

export const metadata: Metadata = {
  title: 'Saved Estimates – PlumbPrice AI',
  description: 'Resume and review recent pricing work.',
}

function EstimatesFallback() {
  return (
    <div className="p-4 space-y-3">
      <div className="mb-3 h-6 w-1/4 skeleton rounded-lg" />
      <div className="skeleton h-16 rounded-xl" />
      <div className="skeleton h-16 rounded-xl" />
      <div className="skeleton h-16 rounded-xl" />
      <div className="skeleton h-16 rounded-xl" />
    </div>
  )
}

export default function Estimates() {
  return (
    <Suspense fallback={<EstimatesFallback />}>
      <EstimatesListPage />
    </Suspense>
  )
}
