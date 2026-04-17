import { useQuery, useMutation, useQueryClient, type UseQueryOptions } from '@tanstack/react-query'
import { api, estimatesApi, type EstimateListItem, type EstimateDetailResponse } from '@/lib/api'

// ─── Query keys ─────────────────────────────────────────────────────────────

export const estimateKeys = {
  all: ['estimates'] as const,
  lists: () => [...estimateKeys.all, 'list'] as const,
  list: (params?: { job_type?: string; status?: string }) =>
    [...estimateKeys.lists(), params ?? {}] as const,
  details: () => [...estimateKeys.all, 'detail'] as const,
  detail: (id: number) => [...estimateKeys.details(), id] as const,
}

// ─── Queries ────────────────────────────────────────────────────────────────

export function useEstimates(
  params?: { job_type?: string; status?: string },
  options?: Partial<UseQueryOptions<EstimateListItem[]>>,
) {
  return useQuery({
    queryKey: ['estimates', { filter: params?.job_type ?? 'all' }],
    queryFn: async () => {
      const apiParams = params?.job_type && params.job_type !== 'all'
        ? { job_type: params.job_type }
        : {}
      const res = await api.get('/estimates', { params: apiParams })
      const raw = res.data
      return (Array.isArray(raw) ? raw : (raw?.estimates ?? [])) as EstimateListItem[]
    },
    ...options,
  })
}

export function useEstimate(
  id: number,
  options?: Partial<UseQueryOptions<EstimateDetailResponse>>,
) {
  return useQuery({
    queryKey: ['estimates', id],
    queryFn: async () => {
      const res = await api.get(`/estimates/${id}`)
      return res.data as EstimateDetailResponse
    },
    enabled: !!id,
    ...options,
  })
}

// ─── Mutations ──────────────────────────────────────────────────────────────

export function useCreateEstimate() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (body: { type: 'service' | 'construction'; data: Record<string, unknown> }) => {
      const res = body.type === 'service'
        ? await estimatesApi.createService(body.data)
        : await estimatesApi.createConstruction(body.data)
      return res.data
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['estimates'] })
    },
  })
}

export function useDeleteEstimate() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: number) => api.delete(`/estimates/${id}`),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['estimates'] })
    },
  })
}

export function useDuplicateEstimate() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (id: number) => {
      const res = await api.post(`/estimates/${id}/duplicate`, {})
      return res.data as EstimateListItem & { id: number }
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['estimates'] })
    },
  })
}
