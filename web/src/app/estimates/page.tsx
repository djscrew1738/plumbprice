'use client'

import { Suspense } from 'react'
import { EstimatesListPage } from '@/components/estimates/EstimatesListPage'

export default function Estimates() {
  return (
    <Suspense>
      <EstimatesListPage />
    </Suspense>
  )
}
