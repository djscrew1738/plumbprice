import { PageShell } from '@/components/layout/shell'
import { PageHeader } from '@/components/layout/shell/PageHeader'
import { Skeleton } from '@/components/ui/Skeleton'

export default function DocumentsLoading() {
  return (
    <PageShell>
      <PageHeader.Skeleton />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} variant="card" className="h-40 rounded-[var(--radius-lg)]" />
        ))}
      </div>
    </PageShell>
  )
}
