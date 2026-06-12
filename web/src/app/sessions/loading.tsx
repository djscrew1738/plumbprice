import { PageShell } from '@/components/layout/shell'
import { PageHeader } from '@/components/layout/shell/PageHeader'
import { Skeleton } from '@/components/ui/Skeleton'

export default function SessionsLoading() {
  return (
    <PageShell>
      <PageHeader.Skeleton />
      <div className="space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="flex items-center gap-3 rounded-[var(--radius-lg)] bg-[color:var(--panel)] p-4">
            <Skeleton variant="avatar" className="h-10 w-10 rounded-full" />
            <div className="flex-1 space-y-2">
              <Skeleton variant="text" className="h-4 w-1/3 rounded-md" />
              <Skeleton variant="text" className="h-3 w-1/2 rounded-md" />
            </div>
          </div>
        ))}
      </div>
    </PageShell>
  )
}
