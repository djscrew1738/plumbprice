import { useQuery, useMutation, useQueryClient, type UseQueryOptions } from '@tanstack/react-query'
import { api, estimatesApi, type EstimateListItem, type EstimateDetailResponse } from '@/lib/api'
import { useToast } from '@/components/ui/Toast'

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
    queryKey: estimateKeys.list(params),
    staleTime: 5 * 60_000,
    queryFn: async () => {
      const apiParams: Record<string, string> = {}
      if (params?.job_type && params.job_type !== 'all') apiParams.job_type = params.job_type
      if (params?.status && params.status !== 'all') apiParams.status = params.status
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
    queryKey: estimateKeys.detail(id),
    staleTime: 5 * 60_000,
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
  const toast = useToast()

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
    onError: () => {
      toast.error('Failed to create estimate')
    },
  })
}

export function useDeleteEstimate() {
  const queryClient = useQueryClient()
  const toast = useToast()

  return useMutation({
    mutationFn: (id: number) => api.delete(`/estimates/${id}`),
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: ['estimates'] })
      const previousQueries = queryClient.getQueriesData<EstimateListItem[]>({ queryKey: ['estimates'] })
      queryClient.setQueriesData<EstimateListItem[]>(
        { queryKey: ['estimates'] },
        (old) => old?.filter(e => e.id !== id),
      )
      return { previousQueries }
    },
    onError: (_err, _id, context) => {
      context?.previousQueries?.forEach(([key, data]) => {
        queryClient.setQueryData(key, data)
      })
      toast.error('Failed to delete estimate')
    },
    onSuccess: () => {
      toast.success('Estimate deleted')
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: ['estimates'] })
    },
  })
}

export function useDuplicateEstimate() {
  const queryClient = useQueryClient()
  const toast = useToast()

  return useMutation({
    mutationFn: async (id: number) => {
      const res = await api.post(`/estimates/${id}/duplicate`, {})
      return res.data as EstimateListItem & { id: number }
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['estimates'] })
    },
    onError: () => {
      toast.error('Failed to duplicate estimate')
    },
  })
}
