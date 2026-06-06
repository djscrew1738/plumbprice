'use client'

import { useState, type ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider } from '@/contexts/AuthContext'
import { ToastProvider } from '@/components/ui/Toast'
import { ErrorBoundary, ErrorFallback } from '@/components/ui/ErrorBoundary'
import { QUERY_STALE_TIME_MS, QUERY_GC_TIME_MS } from '@/lib/constants'

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: QUERY_STALE_TIME_MS,
        gcTime: QUERY_GC_TIME_MS,
        retry: 1,
        refetchOnWindowFocus: false,
      },
    },
  }))

  return (
    <ErrorBoundary
      fallback={
        <ErrorFallback
          message="We're having trouble loading PlumbPrice AI. Please try refreshing."
          onRetry={() => window.location.reload()}
        />
      }
    >
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <ToastProvider>
            {children}
          </ToastProvider>
        </AuthProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  )
}
