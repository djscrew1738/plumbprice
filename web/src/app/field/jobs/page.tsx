'use client'

/**
 * Field Jobs page — /field/jobs
 *
 * Lists assigned jobs for the field tech with status and close-job action.
 */

import { useRouter } from 'next/navigation'
import { ArrowLeft, Briefcase, CheckCircle, Clock, AlertCircle } from 'lucide-react'
import { useSafeQuery } from '@/lib/hooks'
import { api } from '@/lib/api'
import { formatCurrency } from '@/lib/utils'
import type { EstimateListItem as Estimate } from '@/types'

function useFieldJobs() {
  return useSafeQuery(
    {
      queryKey: ['field-jobs'],
      queryFn: () =>
        api
          .get<{ estimates: Estimate[] }>('/estimates?status=draft,sent&limit=20')
          .then((r) => r.data.estimates),
      staleTime: 30_000,
    },
    []
  )
}

export default function FieldJobsPage() {
  const router = useRouter()
  const { data: jobs, isLoading, isError, refetch } = useFieldJobs()

  return (
    <div className="flex flex-col min-h-screen bg-background">
      <header className="sticky top-0 z-10 bg-background border-b border-border-subtle px-4 py-3 flex items-center gap-3">
        <button
          onClick={() => router.back()}
          className="p-2 -ml-2 rounded-lg hover:bg-surface-1 min-h-[44px] min-w-[44px] flex items-center justify-center"
          aria-label="Back"
        >
          <ArrowLeft className="h-5 w-5" />
        </button>
        <h1 className="text-base font-semibold">My Jobs</h1>
      </header>

      <main className="flex-1 p-4 space-y-3">
        {isLoading && (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-20 rounded-xl bg-surface-1 animate-pulse" />
            ))}
          </div>
        )}

        {isError && (
          <div className="rounded-xl bg-red-50 border border-red-200 p-4 text-center">
            <AlertCircle className="h-6 w-6 text-red-500 mx-auto mb-2" />
            <p className="text-sm text-red-700">Failed to load jobs</p>
            <button
              onClick={() => void refetch()}
              className="mt-2 text-sm text-red-600 underline min-h-[44px]"
            >
              Retry
            </button>
          </div>
        )}

        {!isLoading && !isError && jobs.length === 0 && (
          <div className="rounded-xl bg-surface-1 border border-border-subtle p-8 text-center">
            <Briefcase className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
            <p className="text-muted-foreground text-sm">No active jobs</p>
          </div>
        )}

        {jobs.map((job) => (
          <JobCard key={job.id} job={job} onPress={() => router.push(`/field/jobs/${job.id}`)} />
        ))}
      </main>
    </div>
  )
}

function JobCard({ job, onPress }: { job: Estimate; onPress: () => void }) {
  const statusIcon = {
    draft: <Clock className="h-4 w-4 text-yellow-500" />,
    sent: <CheckCircle className="h-4 w-4 text-blue-500" />,
    won: <CheckCircle className="h-4 w-4 text-green-500" />,
  }[job.status ?? 'draft'] ?? <Clock className="h-4 w-4 text-muted-foreground" />

  return (
    <button
      onClick={onPress}
      className="w-full flex items-start gap-3 p-4 rounded-xl border border-border-subtle bg-card active:scale-[0.98] transition-transform text-left min-h-[72px]"
    >
      <div className="mt-0.5">{statusIcon}</div>
      <div className="flex-1 min-w-0">
        <p className="font-medium text-sm truncate">{job.title ?? `Job #${job.id}`}</p>
        <p className="text-xs text-muted-foreground truncate">{job.county ?? '—'}</p>
      </div>
      <div className="text-right flex-shrink-0">
        <p className="font-semibold text-sm text-foreground">
          {job.grand_total != null ? formatCurrency(job.grand_total) : '—'}
        </p>
        <p className="text-xs text-muted-foreground capitalize">{job.status ?? 'draft'}</p>
      </div>
    </button>
  )
}
