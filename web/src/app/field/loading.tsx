import { PageShell } from '@/components/layout/shell'
import { PageHeader } from '@/components/layout/shell/PageHeader'
import { Skeleton } from '@/components/ui/Skeleton'

export default function FieldLoading() {
  return (
    <PageShell>
      <PageHeader.Skeleton />
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} variant="card" className="h-32 rounded-[var(--radius-lg)]" />
        ))}
      </div>
    </PageShell>
  )
}
