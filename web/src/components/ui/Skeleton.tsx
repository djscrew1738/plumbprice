'use client'

export function PageSkeleton() {
  return (
    <div className="p-4">
      <div className="mb-4 h-8 w-1/3 skeleton rounded-lg" />
      <div className="space-y-3">
        <div className="h-16 skeleton rounded-xl" />
        <div className="h-16 skeleton rounded-xl" />
        <div className="h-16 skeleton rounded-xl" />
        <div className="h-16 skeleton rounded-xl" />
      </div>
    </div>
  )
}

export function ListSkeleton({ count = 5 }: { count?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="skeleton flex h-16 w-full items-center gap-3 rounded-xl p-3">
          <div className="h-10 w-10 skeleton shrink-0 rounded-lg" />
          <div className="flex-1 space-y-2">
            <div className="h-3 skeleton w-2/3 rounded" />
            <div className="h-2 skeleton w-1/2 rounded" />
          </div>
        </div>
      ))}
    </div>
  )
}

export function CardSkeleton() {
  return (
    <div className="skeleton rounded-2xl p-4">
      <div className="mb-3 h-5 w-1/2 skeleton rounded" />
      <div className="h-3 skeleton w-full rounded" />
      <div className="mt-2 h-3 skeleton w-2/3 rounded" />
    </div>
  )
}

export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-1">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="skeleton flex h-12 items-center justify-between rounded-lg px-4">
          <div className="h-4 w-1/4 skeleton rounded" />
          <div className="h-4 w-1/6 skeleton rounded" />
          <div className="h-4 w-1/6 skeleton rounded" />
        </div>
      ))}
    </div>
  )
}

export function ChatSkeleton() {
  return (
    <div className="flex flex-col gap-4 p-3">
      <div className="flex gap-3">
        <div className="h-6 w-6 skeleton shrink-0 rounded-full" />
        <div className="flex-1 space-y-2">
          <div className="h-4 skeleton w-full rounded-lg" />
          <div className="h-4 skeleton w-3/4 rounded-lg" />
        </div>
      </div>
      <div className="ml-auto flex gap-3">
        <div className="h-4 max-w-[80%] skeleton rounded-lg rounded-bl-sm bg-[color:var(--accent)] px-4 py-2" />
      </div>
    </div>
  )
}

export function EmptyStateSkeleton() {
  return (
    <div className="flex h-[400px] flex-col items-center justify-center gap-4">
      <div className="h-16 w-16 skeleton shrink-0 rounded-2xl" />
      <div className="h-4 w-48 skeleton rounded" />
      <div className="h-3 w-72 skeleton rounded" />
    </div>
  )
}
