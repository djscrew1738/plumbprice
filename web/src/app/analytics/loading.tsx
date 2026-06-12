import { PageShell } from '@/components/layout/shell'
import { PageHeader } from '@/components/layout/shell/PageHeader'
import { Skeleton } from '@/components/ui/Skeleton'

export default function AnalyticsLoading() {
  return (
    <PageShell>
      <PageHeader.Skeleton />
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} variant="stat-card" className="h-24 rounded-[var(--radius-lg)]" />
        ))}
      </div>
      <div className="mt-6 grid gap-4 md:grid-cols-2">
        <Skeleton variant="card" className="h-64 rounded-[var(--radius-lg)]" />
        <Skeleton variant="card" className="h-64 rounded-[var(--radius-lg)]" />
      </div>
    </PageShell>
  )
}
