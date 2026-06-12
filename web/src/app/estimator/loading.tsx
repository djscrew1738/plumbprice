import { Skeleton } from '@/components/ui/Skeleton'

export default function EstimatorLoading() {
  return (
    <div className="flex h-[calc(100dvh-var(--header-height))] flex-col">
      {/* Chat area skeleton */}
      <div className="flex-1 space-y-4 p-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className={`flex gap-3 ${i % 2 === 1 ? 'flex-row-reverse' : ''}`}
          >
            <Skeleton variant="avatar" className="h-8 w-8 shrink-0 rounded-full" />
            <Skeleton
              variant="card"
              className={`h-20 rounded-2xl ${i % 2 === 1 ? 'w-2/3' : 'w-3/4'}`}
            />
          </div>
        ))}
      </div>
      {/* Input bar skeleton */}
      <div className="border-t border-[color:var(--line)] p-4">
        <Skeleton variant="text" className="h-12 w-full rounded-xl" />
      </div>
    </div>
  )
}
