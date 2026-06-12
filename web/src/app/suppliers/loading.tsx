import { PageShell } from '@/components/layout/shell'
import { PageHeader } from '@/components/layout/shell/PageHeader'
import { Skeleton } from '@/components/ui/Skeleton'

export default function SuppliersLoading() {
  return (
    <PageShell>
      <PageHeader.Skeleton />
      <div className="space-y-3">
        <Skeleton variant="text" className="h-10 w-full rounded-lg" />
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} variant="table-row" className="h-14 rounded-lg" />
        ))}
      </div>
    </PageShell>
  )
}
