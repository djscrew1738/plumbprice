import { PageShell } from '@/components/layout/shell'
import { PageHeader } from '@/components/layout/shell/PageHeader'
import { Skeleton } from '@/components/ui/Skeleton'

export default function SettingsLoading() {
  return (
    <PageShell>
      <PageHeader.Skeleton />
      <div className="space-y-6">
        <Skeleton variant="card" className="h-64 rounded-[var(--radius-lg)]" />
        <Skeleton variant="card" className="h-48 rounded-[var(--radius-lg)]" />
      </div>
    </PageShell>
  )
}
