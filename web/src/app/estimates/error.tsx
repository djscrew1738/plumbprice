'use client'

import { useEffect } from 'react'
import { ErrorState } from '@/components/ui/ErrorState'

export default function EstimatesError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    if (process.env.NODE_ENV === 'development') {
      console.error('Estimates page error:', error)
    }
  }, [error])

  return (
    <div className="min-h-[60dvh] p-4 sm:p-6 lg:p-8">
      <div className="mx-auto max-w-5xl">
        <ErrorState
          message={error.message || 'Failed to load estimates.'}
          onRetry={reset}
          className="mt-8"
        />
      </div>
    </div>
  )
}
