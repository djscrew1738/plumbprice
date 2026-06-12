import { PageShell } from '@/components/layout/shell'
import { PageHeader } from '@/components/layout/shell/PageHeader'
import { Skeleton } from '@/components/ui/Skeleton'

export default function ProjectLoading() {
  return (
    <PageShell>
      <PageHeader.Skeleton />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="space-y-3 lg:col-span-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} variant="card" className="h-24 rounded-[var(--radius-lg)]" />
          ))}
        </div>
        <div className="space-y-3">
          <Skeleton variant="card" className="h-40 rounded-[var(--radius-lg)]" />
          <Skeleton variant="card" className="h-32 rounded-[var(--radius-lg)]" />
        </div>
      </div>
    </PageShell>
  )
}
