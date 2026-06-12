'use client'

import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { MessageSquare } from 'lucide-react'
import { cn, formatRelativeTime } from '@/lib/utils'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/Button'
import { Skeleton } from '@/components/ui/Skeleton'
import { useToast } from '@/components/ui/Toast'
import { ACTIVITY_ICON, summarizeActivity, type ActivityEntry } from '@/lib/activity'

interface ProjectActivityTabProps {
  projectId: number
}

export function ProjectActivityTab({ projectId }: ProjectActivityTabProps) {
  const qc = useQueryClient()
  const toast = useToast()
  const [note, setNote] = useState('')
  const [posting, setPosting] = useState(false)

  const { data, isLoading, error } = useQuery({
    queryKey: ['project-activity', projectId],
    queryFn: async () => {
      const res = await api.get<ActivityEntry[]>(`/projects/${projectId}/activity`, {
        params: { limit: 50 },
      })
      return res.data
    },
  })

  const postNote = async () => {
    const trimmed = note.trim()
    if (!trimmed) return
    setPosting(true)
    try {
      await api.post(`/projects/${projectId}/activity`, { note: trimmed })
      setNote('')
      await qc.invalidateQueries({ queryKey: ['project-activity', projectId] })
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Could not add note'
      toast.error('Failed to add note', msg)
    } finally {
      setPosting(false)
    }
  }

  return (
    <div className="space-y-4 p-5">
      {/* Note input */}
      <div className="space-y-2 rounded-xl border border-white/[0.06] bg-white/[0.02] p-3">
        <label htmlFor="activity-note" className="block text-[10px] font-bold uppercase tracking-wider text-zinc-600">
          Add note
        </label>
        <textarea
          id="activity-note"
          value={note}
          onChange={e => setNote(e.target.value)}
          rows={3}
          maxLength={2000}
          placeholder="Leave a note for the team…"
          className="input w-full resize-none text-sm"
        />
        <div className="flex justify-end">
          <Button
            variant="primary"
            size="sm"
            disabled={posting || !note.trim()}
            onClick={() => void postNote()}
            isLoading={posting}
          >
            <MessageSquare size={12} />
            Add note
          </Button>
        </div>
      </div>

      {/* Timeline */}
      {isLoading && (
        <div className="space-y-2">
          <Skeleton variant="card" className="h-12" />
          <Skeleton variant="card" className="h-12" />
          <Skeleton variant="card" className="h-12" />
        </div>
      )}

      {!isLoading && error && (
        <div className="text-xs text-red-400">Could not load activity.</div>
      )}

      {!isLoading && !error && data && data.length === 0 && (
        <div className="rounded-xl border border-dashed border-white/[0.07] bg-white/[0.02] p-5 text-center">
          <p className="text-xs text-zinc-600">
            No activity yet. Stage changes, notes, and proposals will appear here.
          </p>
        </div>
      )}

      {!isLoading && !error && data && data.length > 0 && (
        <ol className="space-y-2">
          {data.map(entry => {
            const meta = ACTIVITY_ICON[entry.kind] ?? { icon: MessageSquare, className: 'text-zinc-400' }
            const Icon = meta.icon
            const actorName = entry.actor?.full_name || entry.actor?.email || 'Someone'
            const when = formatRelativeTime(entry.created_at)
            return (
              <li
                key={entry.id}
                className="flex gap-3 rounded-xl border border-white/[0.06] bg-white/[0.02] p-3"
              >
                <div className={cn('mt-0.5 shrink-0', meta.className)}>
                  <Icon size={14} />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="whitespace-pre-wrap break-words text-xs leading-snug text-zinc-200">
                    {summarizeActivity(entry.kind, entry.payload)}
                  </div>
                  <div className="mt-0.5 text-[10px] text-zinc-600">
                    {actorName} · {when}
                  </div>
                </div>
              </li>
            )
          })}
        </ol>
      )}
    </div>
  )
}
