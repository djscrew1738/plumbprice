import { PageShell } from '@/components/layout/shell'
import { PageHeader } from '@/components/layout/shell/PageHeader'
import { Skeleton } from '@/components/ui/Skeleton'

export default function ProposalsLoading() {
  return (
    <PageShell>
      <PageHeader.Skeleton />
      <div className="space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} variant="card" className="h-24 rounded-[var(--radius-lg)]" />
        ))}
      </div>
    </PageShell>
  )
}
