import { useQuery, useMutation, useQueryClient, type UseQueryOptions } from '@tanstack/react-query'
import { blueprintsApi } from '@/lib/api'

// ─── Query keys ─────────────────────────────────────────────────────────────

export const blueprintKeys = {
  all: ['blueprints'] as const,
  poll: () => ['blueprint-poll'] as const,
  takeoff: (jobId: string) => ['blueprint-takeoff', jobId] as const,
}

// ─── Types ──────────────────────────────────────────────────────────────────

export type JobStatus = 'queued' | 'processing' | 'completed' | 'failed'

export interface BlueprintJob {
  id: string
  filename: string
  pages: number
  status: JobStatus
  uploaded_at: string
  message?: string
}

// ─── Queries ────────────────────────────────────────────────────────────────

export function useBlueprints(
  options?: Partial<UseQueryOptions<BlueprintJob[]>>,
) {
  return useQuery({
    queryKey: blueprintKeys.all,
    queryFn: async () => {
      const res = await blueprintsApi.list()
      return (Array.isArray(res.data) ? res.data : res.data?.jobs ?? []) as BlueprintJob[]
    },
    ...options,
  })
}

// ─── Mutations ──────────────────────────────────────────────────────────────

export function useUploadBlueprint() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (file: File) => {
      const res = await blueprintsApi.upload(file)
      return res.data
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: blueprintKeys.all })
    },
  })
}

export function useDeleteBlueprint() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (jobId: string) => blueprintsApi.delete(jobId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: blueprintKeys.all })
    },
  })
}
