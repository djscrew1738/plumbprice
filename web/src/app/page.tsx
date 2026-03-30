'use client'

import { Suspense } from 'react'
import { LauncherHome, LauncherHomeSkeleton } from '@/components/workspace/LauncherHome'
import { PageSkeleton } from '@/components/ui/Skeleton'

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
