'use client'

import { useState, useMemo, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { MessageSquare, Trash2, ArrowUpDown, Clock, Hash, Copy } from 'lucide-react'
import { useSessions, useDeleteSession, useCloneSession } from '@/lib/hooks'
import { useToast } from '@/components/ui/Toast'
import { SearchInput } from '@/components/ui/SearchInput'
import { Badge } from '@/components/ui/Badge'
import dynamic from 'next/dynamic'
import { Tooltip } from '@/components/ui/Tooltip'

const ConfirmDialog = dynamic(() => import('@/components/ui/ConfirmDialog').then(m => ({ default: m.ConfirmDialog })), { ssr: false })
import { EmptyState } from '@/components/ui/EmptyState'
import { cn } from '@/lib/utils'

type SortKey = 'recent' | 'oldest' | 'messages'

function formatRelativeTime(dateStr: string): string {
  const now = Date.now()
  const then = new Date(dateStr).getTime()
  const diff = now - then

  const seconds = Math.floor(diff / 1000)
  if (seconds < 60) return 'just now'
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  if (days < 30) return `${days}d ago`
  const months = Math.floor(days / 30)
  return `${months}mo ago`
}

export function SessionHistoryPage() {
  const router = useRouter()
  const toast = useToast()
  const { data: sessions, isLoading } = useSessions()
  const deleteSession = useDeleteSession()
  const cloneSession = useCloneSession()

  const [search, setSearch] = useState('')
  const [sortKey, setSortKey] = useState<SortKey>('recent')
  const [deleteTarget, setDeleteTarget] = useState<number | null>(null)

  const filtered = useMemo(() => {
    if (!sessions) return []
    let result = sessions
    if (search.trim()) {
      const q = search.toLowerCase()
      result = result.filter(
        (s) => (s.title ?? 'untitled session').toLowerCase().includes(q),
      )
    }
    const sorted = [...result]
    switch (sortKey) {
      case 'recent':
        sorted.sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
        break
      case 'oldest':
        sorted.sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
        break
      case 'messages':
        sorted.sort((a, b) => (b.message_count ?? 0) - (a.message_count ?? 0))
        break
    }
    return sorted
  }, [sessions, search, sortKey])

  const handleResume = useCallback(
    (id: number) => {
      router.push(`/estimator?session=${id}`)
    },
    [router],
  )

  const handleConfirmDelete = useCallback(() => {
    if (deleteTarget == null) return
    deleteSession.mutate(deleteTarget)
    setDeleteTarget(null)
  }, [deleteTarget, deleteSession])

  const handleClone = useCallback(
    (e: React.MouseEvent, id: number) => {
      e.stopPropagation()
      cloneSession.mutate(id, {
        onSuccess: (res) => {
          toast.success('Session cloned', 'Opening cloned session…')
          router.push(`/estimator?session=${res.data.id}`)
        },
        onError: () => toast.error('Could not clone session', 'Please try again.'),
      })
    },
    [cloneSession, router, toast],
  )

  const cycleSortKey = useCallback(() => {
    setSortKey((prev) => {
      if (prev === 'recent') return 'oldest'
      if (prev === 'oldest') return 'messages'
      return 'recent'
    })
  }, [])

  const sortLabel: Record<SortKey, string> = {
    recent: 'Most recent',
    oldest: 'Oldest first',
    messages: 'Most messages',
  }

  if (isLoading) {
    return (
      <div className="mx-auto w-full max-w-3xl px-4 py-8">
        <h1 className="text-xl font-semibold text-[color:var(--ink)]">Chat History</h1>
        <div className="mt-6 space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className="h-20 animate-pulse rounded-xl border border-[color:var(--line)] bg-[color:var(--panel-strong)]"
            />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-xl font-semibold text-[color:var(--ink)]">Chat History</h1>

        <div className="flex items-center gap-2">
          <SearchInput
            value={search}
            onChange={setSearch}
            placeholder="Search sessions…"
            className="w-full sm:w-56"
          />
          <Tooltip content={`Sort: ${sortLabel[sortKey]}`} side="bottom">
            <button
              type="button"
              onClick={cycleSortKey}
              className={cn(
                'flex min-h-[36px] min-w-[36px] items-center justify-center rounded-xl border border-[color:var(--line)]',
                'bg-[color:var(--panel)] text-[color:var(--muted-ink)] transition-colors',
                'hover:bg-[color:var(--panel-strong)] hover:text-[color:var(--ink)]',
              )}
              aria-label={`Sort by ${sortLabel[sortKey]}`}
            >
              {sortKey === 'recent' && <Clock size={16} />}
              {sortKey === 'oldest' && <ArrowUpDown size={16} />}
              {sortKey === 'messages' && <Hash size={16} />}
            </button>
          </Tooltip>
        </div>
      </div>

      {filtered.length === 0 && !search && (
        <div className="mt-16">
          <EmptyState
            icon={<MessageSquare size={24} />}
            title="No chat sessions yet"
            description="Start a conversation in the Estimator to create your first session."
            action={
              <button
                type="button"
                onClick={() => router.push('/estimator')}
                className={cn(
                  'inline-flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition-all',
                  'bg-gradient-to-br from-[color:var(--accent)] to-[color:var(--accent-strong)] text-white',
                  'hover:shadow-[0_6px_18px_hsl(var(--accent-hsl)/0.36)] active:scale-[0.98]',
                )}
              >
                <MessageSquare size={14} />
                Open Estimator
              </button>
            }
          />
        </div>
      )}

      {filtered.length === 0 && search && (
        <div className="mt-16">
          <EmptyState
            icon={<MessageSquare size={24} />}
            title="No matching sessions"
            description={`No sessions match "${search}". Try a different search term.`}
          />
        </div>
      )}

      {filtered.length > 0 && (
        <div className="mt-6 space-y-3">
          {filtered.map((session) => {
            const msgCount = session.message_count
            const lastMsg = session.last_message_at

            return (
              <button
                key={session.id}
                type="button"
                onClick={() => handleResume(session.id)}
                className={cn(
                  'group flex w-full items-start gap-3 rounded-xl border border-[color:var(--line)] p-4 text-left transition-all',
                  'bg-[color:var(--panel)] hover:bg-[color:var(--panel-strong)] hover:border-[color:var(--accent)]/30',
                  'hover:shadow-sm active:scale-[0.995]',
                )}
              >
                <div className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-[color:var(--accent-soft)] text-[color:var(--accent-strong)]">
                  <MessageSquare size={18} />
                </div>

                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <h3 className="truncate text-sm font-semibold text-[color:var(--ink)]">
                      {session.title || 'Untitled Session'}
                    </h3>
                    {msgCount != null && (
                      <Badge variant="neutral" size="sm">
                        {msgCount} msg{msgCount !== 1 ? 's' : ''}
                      </Badge>
                    )}
                  </div>
                  <p className="mt-0.5 text-xs text-[color:var(--muted-ink)]">
                    {formatRelativeTime(lastMsg ?? session.updated_at)}
                    {session.county && <> · {session.county} County</>}
                  </p>
                </div>

                <Tooltip content="Clone session" side="left">
                  <span
                    role="button"
                    tabIndex={0}
                    onClick={(e) => handleClone(e, session.id)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault()
                        handleClone(e as unknown as React.MouseEvent, session.id)
                      }
                    }}
                    className={cn(
                      'flex min-h-[32px] min-w-[32px] items-center justify-center rounded-lg p-1.5 transition-colors',
                      'text-[color:var(--muted-ink)] opacity-0 group-hover:opacity-100',
                      'hover:bg-[color:var(--panel-strong)] hover:text-[color:var(--ink)]',
                    )}
                    aria-label="Clone session"
                  >
                    <Copy size={15} />
                  </span>
                </Tooltip>

                <Tooltip content="Delete session" side="left">
                  <span
                    role="button"
                    tabIndex={0}
                    onClick={(e) => {
                      e.stopPropagation()
                      setDeleteTarget(session.id)
                    }}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault()
                        e.stopPropagation()
                        setDeleteTarget(session.id)
                      }
                    }}
                    className={cn(
                      'flex min-h-[32px] min-w-[32px] items-center justify-center rounded-lg p-1.5 transition-colors',
                      'text-[color:var(--muted-ink)] opacity-0 group-hover:opacity-100',
                      'hover:bg-[hsl(var(--danger)/0.1)] hover:text-[hsl(var(--danger))]',
                    )}
                    aria-label="Delete session"
                  >
                    <Trash2 size={15} />
                  </span>
                </Tooltip>
              </button>
            )
          })}
        </div>
      )}

      <ConfirmDialog
        open={deleteTarget != null}
        onClose={() => setDeleteTarget(null)}
        onConfirm={handleConfirmDelete}
        title="Delete chat session?"
        description="This will permanently delete this session and all its messages. This action cannot be undone."
        confirmLabel="Delete"
        variant="danger"
        isLoading={deleteSession.isPending}
      />
    </div>
  )
}
