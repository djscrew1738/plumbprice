import { PageShell } from '@/components/layout/shell'
import { PageHeader } from '@/components/layout/shell/PageHeader'
import { Skeleton } from '@/components/ui/Skeleton'

export default function AdminLoading() {
  return (
    <PageShell width="narrow">
      <PageHeader.Skeleton />
      <div className="space-y-3">
        <Skeleton variant="text" className="h-10 w-full rounded-lg" />
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} variant="card" className="h-32 rounded-[var(--radius-lg)]" />
        ))}
      </div>
    </PageShell>
  )
}
