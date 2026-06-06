import { cookies } from 'next/headers'
import { Suspense } from 'react'
import { LauncherHome } from '@/components/workspace/LauncherHome'
import { LauncherHomeSkeleton } from '@/components/workspace/LauncherHome'
import { PublicHome } from '@/components/workspace/PublicHome'

function HomeContent() {
  return <LauncherHome />
}

export default async function Home() {
  const cookieStore = await cookies()

  if (!cookieStore.get('pp_token')?.value) {
    return <PublicHome />
  }

  return (
    <Suspense fallback={<LauncherHomeSkeleton />}>
      <HomeContent />
    </Suspense>
  )
}
