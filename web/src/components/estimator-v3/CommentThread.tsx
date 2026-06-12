'use client'

import { useState, useCallback, useEffect } from 'react'
import { MessageCircle, Send, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { estimatesApi } from '@/lib/api/estimates'
import { haptic } from '@/lib/haptics'

interface Comment {
  id: number
  estimate_id: number
  user_id: number
  parent_id: number | null
  content: string
  created_at: string | null
  user_name: string | null
}

interface CommentThreadProps {
  estimateId: number
  className?: string
}

export function CommentThread({ estimateId, className }: CommentThreadProps) {
  const [comments, setComments] = useState<Comment[]>([])
  const [input, setInput] = useState('')
  const [replyTo, setReplyTo] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)
  const [open, setOpen] = useState(false)

  const load = useCallback(async () => {
    try {
      const res = await estimatesApi.getComments(estimateId)
      setComments(res.data.comments)
    } catch {
      // ignore
    }
  }, [estimateId])

  useEffect(() => {
    if (open) load()
  }, [open, load])

  const handleSubmit = async () => {
    if (!input.trim()) return
    setLoading(true)
    try {
      await estimatesApi.createComment(estimateId, { content: input, parent_id: replyTo })
      setInput('')
      setReplyTo(null)
      await load()
      haptic('success')
    } catch {
      haptic('error')
    } finally {
      setLoading(false)
    }
  }

  const topLevel = comments.filter(c => c.parent_id === null)
  const replies = (parentId: number) => comments.filter(c => c.parent_id === parentId)

  return (
    <div className={cn('relative', className)}>
      <button
        type="button"
        onClick={() => { haptic('tap'); setOpen(o => !o) }}
        className="inline-flex items-center gap-1.5 rounded-lg border border-[color:var(--line)] bg-[color:var(--panel-strong)] px-3 py-1.5 text-[11px] font-medium text-[color:var(--muted-ink)] hover:bg-[color:var(--panel)] transition-colors"
      >
        <MessageCircle size={12} />
        Comments {comments.length > 0 && <span className="text-[color:var(--accent-strong)]">({comments.length})</span>}
      </button>

      {open && (
        <div className="absolute right-0 top-full z-20 mt-2 w-72 rounded-xl border border-[color:var(--line)] bg-[color:var(--panel)] p-3 shadow-xl">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-[color:var(--muted-ink)]">Comments</span>
            <button type="button" onClick={() => setOpen(false)} className="rounded p-1 text-[color:var(--muted-ink)] hover:bg-[color:var(--panel-strong)]">
              <X size={12} />
            </button>
          </div>

          <div className="max-h-48 overflow-y-auto space-y-2">
            {topLevel.length === 0 && (
              <p className="py-4 text-center text-[11px] text-[color:var(--muted-ink)]">No comments yet</p>
            )}
            {topLevel.map(comment => (
              <div key={comment.id} className="space-y-1">
                <div className="rounded-lg bg-[color:var(--panel-strong)] px-2.5 py-2">
                  <div className="mb-0.5 flex items-center justify-between">
                    <span className="text-[10px] font-semibold text-[color:var(--ink)]">{comment.user_name || 'User'}</span>
                    <span className="text-[9px] text-[color:var(--muted-ink)]">
                      {comment.created_at ? new Date(comment.created_at).toLocaleDateString() : ''}
                    </span>
                  </div>
                  <p className="text-[11px] text-[color:var(--ink)]">{comment.content}</p>
                  <button
                    type="button"
                    onClick={() => setReplyTo(comment.id)}
                    className="mt-1 text-[9px] text-[color:var(--muted-ink)] hover:text-[color:var(--accent-strong)] transition-colors"
                  >
                    Reply
                  </button>
                </div>
                {replies(comment.id).map(reply => (
                  <div key={reply.id} className="ml-3 rounded-lg bg-[color:var(--panel-strong)]/50 px-2.5 py-1.5">
                    <div className="mb-0.5 flex items-center justify-between">
                      <span className="text-[10px] font-semibold text-[color:var(--ink)]">{reply.user_name || 'User'}</span>
                      <span className="text-[9px] text-[color:var(--muted-ink)]">
                        {reply.created_at ? new Date(reply.created_at).toLocaleDateString() : ''}
                      </span>
                    </div>
                    <p className="text-[11px] text-[color:var(--ink)]">{reply.content}</p>
                  </div>
                ))}
              </div>
            ))}
          </div>

          <div className="mt-2 flex items-end gap-1.5">
            {replyTo && (
              <div className="absolute -top-6 left-2 flex items-center gap-1 rounded-full bg-[color:var(--accent-soft)] px-2 py-0.5 text-[9px] text-[color:var(--accent-strong)]">
                Replying
                <button type="button" onClick={() => setReplyTo(null)}><X size={9} /></button>
              </div>
            )}
            <input
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') handleSubmit() }}
              placeholder="Add a comment…"
              className="input flex-1 rounded-lg px-2.5 py-1.5 text-[11px]"
            />
            <button
              type="button"
              onClick={handleSubmit}
              disabled={loading || !input.trim()}
              className="flex h-7 w-7 items-center justify-center rounded-lg bg-[color:var(--accent)] text-white hover:opacity-90 transition-opacity disabled:opacity-40"
            >
              <Send size={12} />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
