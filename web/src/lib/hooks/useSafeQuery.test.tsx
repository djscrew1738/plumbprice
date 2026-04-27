import { describe, it, expect } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { useSafeQuery } from './useSafeQuery'

function makeWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0, staleTime: 0 } },
  })
  function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }
  return Wrapper
}

describe('useSafeQuery', () => {
  it('returns the fallback while loading', async () => {
    const { result } = renderHook(
      () =>
        useSafeQuery<string[]>(
          {
            queryKey: ['t-loading'],
            queryFn: () => new Promise<string[]>(() => {}), // never resolves
          },
          [],
        ),
      { wrapper: makeWrapper() },
    )
    expect(result.current.data).toEqual([])
    expect(result.current.isLoading).toBe(true)
  })

  it('returns the resolved data on success', async () => {
    const { result } = renderHook(
      () =>
        useSafeQuery<string[]>(
          {
            queryKey: ['t-success'],
            queryFn: async () => ['a', 'b', 'c'],
          },
          [],
        ),
      { wrapper: makeWrapper() },
    )
    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(result.current.data).toEqual(['a', 'b', 'c'])
    expect(result.current.isError).toBe(false)
  })

  it('returns the fallback on error (never undefined)', async () => {
    const { result } = renderHook(
      () =>
        useSafeQuery<string[]>(
          {
            queryKey: ['t-error'],
            queryFn: async () => {
              throw new Error('boom')
            },
          },
          ['fallback-value'],
        ),
      { wrapper: makeWrapper() },
    )
    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(result.current.data).toEqual(['fallback-value'])
    // critical contract: data is never undefined — prevents eternal skeletons.
    expect(result.current.data).not.toBeUndefined()
  })
})
