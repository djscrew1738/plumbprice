import type { Metadata } from 'next'
import { Suspense } from 'react'
import { EstimatorPageV3 } from '@/components/estimator-v3/EstimatorPageV3'
import { EmptyStateSkeleton, ChatSkeleton } from '@/components/ui/Skeleton'

export const metadata: Metadata = {
  title: 'Pricing Workspace – PlumbPrice AI',
  description: 'Build and review a live plumbing estimate powered by AI and real supplier pricing.',
}

function EstimatorPageFallback() {
  return (
    <div className="mx-auto flex min-h-[calc(100vh-12rem)] w-full max-w-6xl flex-col lg:flex-row">
      <div className="flex-1 px-3 py-4">
        <div className="space-y-3">
          <div className="mb-3 h-6 w-1/4 skeleton rounded-lg" />
          <div className="flex gap-2">
            <div className="skeleton h-7 w-20 rounded-full" />
            <div className="skeleton h-7 w-24 rounded-full" />
            <div className="skeleton h-7 w-28 rounded-full" />
          </div>
          <div className="flex flex-col gap-4 py-4">
            <ChatSkeleton />
            <ChatSkeleton />
          </div>
        </div>
      </div>
      <div className="hidden w-[360px] shrink-0 lg:block">
        <div className="shell-panel h-[calc(100vh-12rem)] p-6">
          <EmptyStateSkeleton />
        </div>
      </div>
    </div>
  )
}

export default function Estimator() {
  return (
    <Suspense fallback={<EstimatorPageFallback />}>
      <EstimatorPageV3 />
    </Suspense>
  )
}
