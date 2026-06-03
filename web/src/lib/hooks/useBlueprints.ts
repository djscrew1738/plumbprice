import { useQuery, useMutation, useQueryClient, type UseQueryOptions } from '@tanstack/react-query'
import { blueprintsApi } from '@/lib/api'
import { useToast } from '@/components/ui/Toast'

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
  const toast = useToast()

  return useMutation({
    mutationFn: async (file: File) => {
      const res = await blueprintsApi.upload(file)
      return res.data as { id: string; filename: string; pages?: number; status: JobStatus; uploaded_at: string }
    },
    onMutate: async (file) => {
      await queryClient.cancelQueries({ queryKey: blueprintKeys.all })
      const previous = queryClient.getQueryData<BlueprintJob[]>(blueprintKeys.all)
      const tempId = `temp-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
      const optimisticJob: BlueprintJob = {
        id: tempId,
        filename: file.name,
        pages: 0,
        status: 'queued',
        uploaded_at: new Date().toISOString(),
      }
      queryClient.setQueryData<BlueprintJob[]>(
        blueprintKeys.all,
        (old) => old ? [optimisticJob, ...old] : [optimisticJob],
      )
      return { previous, tempId }
    },
    onSuccess: (data, _file, context) => {
      queryClient.setQueryData<BlueprintJob[]>(blueprintKeys.all, (old) => {
        if (!old) return old
        return old.map(j => j.id === context?.tempId
          ? { id: String(data.id ?? context.tempId), filename: data.filename ?? j.filename, pages: data.pages ?? 0, status: data.status ?? 'queued', uploaded_at: data.uploaded_at ?? j.uploaded_at }
          : j,
        )
      })
      void queryClient.invalidateQueries({ queryKey: blueprintKeys.all })
    },
    onError: (_err, _file, context) => {
      if (context?.previous) {
        queryClient.setQueryData(blueprintKeys.all, context.previous)
      } else {
        // Remove optimistic job if no previous state
        queryClient.setQueryData<BlueprintJob[]>(blueprintKeys.all, (old) =>
          old?.filter(j => j.id !== context?.tempId) ?? old,
        )
      }
      toast.error('Failed to upload blueprint')
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: blueprintKeys.all })
    },
  })
}

export function useDeleteBlueprint() {
  const queryClient = useQueryClient()
  const toast = useToast()

  return useMutation({
    mutationFn: (jobId: string) => blueprintsApi.delete(jobId),
    onMutate: async (jobId) => {
      await queryClient.cancelQueries({ queryKey: blueprintKeys.all })
      const previous = queryClient.getQueryData<BlueprintJob[]>(blueprintKeys.all)
      queryClient.setQueryData<BlueprintJob[]>(
        blueprintKeys.all,
        (old) => old?.filter(b => b.id !== jobId),
      )
      return { previous }
    },
    onError: (_err, _jobId, context) => {
      if (context?.previous) {
        queryClient.setQueryData(blueprintKeys.all, context.previous)
      }
      toast.error('Failed to delete blueprint')
    },
    onSuccess: () => {
      toast.success('Blueprint deleted')
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: blueprintKeys.all })
    },
  })
}
