import { PageShell } from '@/components/layout/shell'
import { PageHeader } from '@/components/layout/shell/PageHeader'
import { Skeleton } from '@/components/ui/Skeleton'

export default function PipelineLoading() {
  return (
    <PageShell>
      <PageHeader.Skeleton />
      <div className="grid grid-cols-1 xl:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, colIdx) => (
          <div key={colIdx} className="space-y-3">
            <Skeleton variant="text" className="h-5 w-24 rounded-lg" />
            {Array.from({ length: 2 }).map((_, i) => (
              <Skeleton key={i} variant="card" className="h-32 rounded-2xl" />
            ))}
          </div>
        ))}
      </div>
    </PageShell>
  )
}
