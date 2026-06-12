'use client'

import { useEffect } from 'react'
import { ErrorState } from '@/components/ui/ErrorState'

export default function AdminError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    if (process.env.NODE_ENV === 'development') {
      console.error('Admin page error:', error)
    }
  }, [error])

  return (
    <div className="min-h-full p-4 sm:p-6 lg:p-8">
      <div className="mx-auto w-full max-w-4xl">
        <ErrorState
          message={error.message || 'Something went wrong loading the admin panel.'}
          onRetry={reset}
          className="mt-8"
        />
      </div>
    </div>
  )
}
