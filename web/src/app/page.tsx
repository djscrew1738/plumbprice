import { Suspense } from 'react'
import { LauncherHome } from '@/components/workspace/LauncherHome'
import { PageSkeleton } from '@/components/ui/Skeleton'

export const dynamic = 'force-dynamic'

function HomeContent() {
  return <LauncherHome />
}

export default function Home() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <HomeContent />
    </Suspense>
  )
}
