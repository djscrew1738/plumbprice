import { Suspense } from 'react'
import { EstimatorPage } from '@/components/estimator/EstimatorPage'

function EstimatorPageFallback() {
  return (
    <div className="mx-auto flex min-h-[calc(100vh-12rem)] w-full max-w-6xl items-center px-4 py-6">
      <div className="shell-panel w-full p-6">
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[color:var(--muted-ink)]">
          Loading pricing workspace...
        </p>
      </div>
    </div>
  )
}

export default function Estimator() {
  return (
    <Suspense fallback={<EstimatorPageFallback />}>
      <EstimatorPage />
    </Suspense>
  )
}
