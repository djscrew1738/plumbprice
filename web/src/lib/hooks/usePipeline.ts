import { useQuery, useMutation, useQueryClient, type UseQueryOptions } from '@tanstack/react-query'
import { projectsApi, type ProjectPipelineResponse, type ProjectPipelineItem } from '@/lib/api'

// ─── Query keys ─────────────────────────────────────────────────────────────

export const pipelineKeys = {
  all: ['projects'] as const,
}

// ─── Queries ────────────────────────────────────────────────────────────────

export function usePipeline(
  options?: Partial<UseQueryOptions<ProjectPipelineResponse>>,
) {
  return useQuery({
    queryKey: pipelineKeys.all,
    queryFn: async () => {
      const response = await projectsApi.list()
      return response.data
    },
    ...options,
  })
}

// ─── Mutations ──────────────────────────────────────────────────────────────

export function useCreateProject() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (body: {
      name: string
      job_type: string
      customer_name?: string
      county?: string
      city?: string
      state?: string
      zip_code?: string
      notes?: string
    }) => {
      const res = await projectsApi.create(body)
      return res.data
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: pipelineKeys.all })
    },
  })
}

export function useMoveProject() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ projectId, newStatus }: { projectId: number; newStatus: string }) => {
      await projectsApi.update(projectId, { status: newStatus })
    },
    onMutate: async ({ projectId, newStatus }) => {
      await queryClient.cancelQueries({ queryKey: pipelineKeys.all })
      const previous = queryClient.getQueryData<ProjectPipelineResponse>(pipelineKeys.all)
      queryClient.setQueryData<ProjectPipelineResponse>(pipelineKeys.all, prev => {
        if (!prev) return prev
        return {
          ...prev,
          projects: prev.projects.map((p: ProjectPipelineItem) =>
            p.id === projectId ? { ...p, status: newStatus } : p
          ),
          summary: (() => {
            const old = prev.projects.find((p: ProjectPipelineItem) => p.id === projectId)
            if (!old) return prev.summary
            const s = { ...prev.summary }
            s[old.status] = Math.max(0, (s[old.status] ?? 1) - 1)
            s[newStatus] = (s[newStatus] ?? 0) + 1
            return s
          })(),
        }
      })
      return { previous }
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(pipelineKeys.all, context.previous)
      }
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: pipelineKeys.all })
    },
  })
}

export function useDeleteProject() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: number) => projectsApi.delete(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: pipelineKeys.all })
    },
  })
}
