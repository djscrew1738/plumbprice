'use client'

import { useState } from 'react'
import dynamic from 'next/dynamic'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { RefreshCw } from 'lucide-react'
import { api } from '@/lib/api'
import { useToast } from '@/components/ui/Toast'
import { PageIntro } from '@/components/layout/PageIntro'

const ConfirmDialog = dynamic(
  () => import('@/components/ui/ConfirmDialog').then(m => ({ default: m.ConfirmDialog })),
  { ssr: false },
)

export interface FailedJobItem {
  type: 'blueprint' | 'document'
  id: number
  original_filename: string | null
  error: string | null
  updated_at: string | null
  task_id: string | null
}

interface FailedJobsResponse {
  count: number
  items: FailedJobItem[]
}

function truncate(text: string, max = 80): string {
  if (!text) return ''
  return text.length > max ? text.slice(0, max - 1) + '…' : text
}

function formatWhen(iso: string | null): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString()
  } catch {
    return iso
  }
}

export function JobsPage() {
  const toast = useToast()
  const queryClient = useQueryClient()
  const [retryTarget, setRetryTarget] = useState<FailedJobItem | null>(null)

  const { data, isLoading, error, refetch, isFetching } = useQuery<FailedJobsResponse>({
    queryKey: ['admin', 'tasks', 'failed'],
    queryFn: async () => {
      const res = await api.get('/admin/tasks', { params: { status: 'failed', limit: 50 } })
      return res.data as FailedJobsResponse
    },
    refetchInterval: 10_000,
  })

  const retryMutation = useMutation({
    mutationFn: async (job: FailedJobItem) => {
      const path = job.type === 'blueprint'
        ? `/admin/blueprints/${job.id}/retry`
        : `/admin/documents/${job.id}/retry`
      const res = await api.post(path)
      return res.data as { task_id: string | null }
    },
    onSuccess: (resp, job) => {
      toast.success('Retry queued', `Task ${resp.task_id ?? 'enqueued'} for ${job.type} #${job.id}`)
      queryClient.invalidateQueries({ queryKey: ['admin', 'tasks', 'failed'] })
    },
    onError: (err: unknown, job) => {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast.error('Retry failed', msg ?? `Could not retry ${job.type} #${job.id}`)
    },
    onSettled: () => setRetryTarget(null),
  })

  const items = data?.items ?? []

  return (
    <div className="mx-auto max-w-6xl p-6 space-y-6">
      <PageIntro
        title="Failed Jobs"
        eyebrow="Worker observability"
        description="Review blueprint and document processing failures and re-enqueue them."
      />

      <div className="flex items-center justify-between">
        <div className="text-sm text-[color:var(--muted)]">
          {isLoading
            ? 'Loading…'
            : `${items.length} failed job${items.length === 1 ? '' : 's'}`}
          {isFetching && !isLoading ? ' · refreshing…' : ''}
        </div>
        <button
          type="button"
          onClick={() => refetch()}
          className="inline-flex items-center gap-2 rounded-md border border-[color:var(--border)] px-3 py-1.5 text-sm hover:bg-[color:var(--panel-hover)]"
        >
          <RefreshCw size={14} />
          Refresh
        </button>
      </div>

      {error ? (
        <div className="rounded-md border border-red-500/30 bg-red-500/5 p-4 text-sm text-red-700 dark:text-red-400">
          Failed to load worker jobs.
        </div>
      ) : items.length === 0 && !isLoading ? (
        <div className="rounded-md border border-[color:var(--border)] bg-[color:var(--panel)] p-10 text-center text-sm text-[color:var(--muted)]">
          No failed jobs — all clear 🎉
        </div>
      ) : (
        <div className="overflow-x-auto rounded-md border border-[color:var(--border)]">
          <table className="w-full text-sm">
            <thead className="bg-[color:var(--panel)] text-left text-[color:var(--muted)]">
              <tr>
                <th className="px-3 py-2 font-medium">Type</th>
                <th className="px-3 py-2 font-medium">Filename</th>
                <th className="px-3 py-2 font-medium">Error</th>
                <th className="px-3 py-2 font-medium">Updated</th>
                <th className="px-3 py-2 font-medium text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              {items.map(job => (
                <tr
                  key={`${job.type}-${job.id}`}
                  className="border-t border-[color:var(--border)]"
                >
                  <td className="px-3 py-2 capitalize">{job.type}</td>
                  <td className="px-3 py-2">{job.original_filename ?? '—'}</td>
                  <td className="px-3 py-2" title={job.error ?? ''}>
                    {job.error ? truncate(job.error, 80) : '—'}
                  </td>
                  <td className="px-3 py-2 text-[color:var(--muted)]">
                    {formatWhen(job.updated_at)}
                  </td>
                  <td className="px-3 py-2 text-right">
                    <button
                      type="button"
                      className="rounded-md border border-[color:var(--border)] px-2 py-1 text-xs hover:bg-[color:var(--panel-hover)] disabled:opacity-50"
                      onClick={() => setRetryTarget(job)}
                      disabled={retryMutation.isPending}
                    >
                      Retry
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <ConfirmDialog
        open={!!retryTarget}
        onClose={() => setRetryTarget(null)}
        onConfirm={() => {
          if (retryTarget) retryMutation.mutate(retryTarget)
        }}
        title="Retry job?"
        description={
          retryTarget
            ? `Re-enqueue ${retryTarget.type} #${retryTarget.id} (${retryTarget.original_filename ?? ''}) for processing?`
            : ''
        }
        confirmLabel="Retry"
        isLoading={retryMutation.isPending}
      />
    </div>
  )
}
