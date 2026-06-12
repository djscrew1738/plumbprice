import { PageShell } from '@/components/layout/shell'
import { Skeleton } from '@/components/ui/Skeleton'

export default function HomeLoading() {
  return (
    <PageShell>
      {/* Hero skeleton */}
      <div className="space-y-4">
        <Skeleton variant="text" className="h-8 w-1/3 rounded-lg" />
        <Skeleton variant="text" className="h-4 w-1/2 rounded-md" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} variant="card" className="h-32 rounded-[var(--radius-xl)]" />
          ))}
        </div>
      </div>

      {/* KPI strip */}
      <div className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} variant="stat-card" className="h-16 rounded-[var(--radius-lg)]" />
        ))}
      </div>

      {/* Recent list */}
      <div className="mt-8 space-y-3">
        <Skeleton variant="text" className="h-5 w-32 rounded-md" />
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} variant="card" className="h-16 rounded-[var(--radius-lg)]" />
        ))}
      </div>
    </PageShell>
  )
}
