'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Brain, Trash2, Plus, Sparkles } from 'lucide-react'
import { memoriesApi, type AgentMemory, type MemoryKind } from '@/lib/api'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Badge } from '@/components/ui/Badge'

const KINDS: { value: MemoryKind; label: string; description: string }[] = [
  { value: 'profile', label: 'Profile', description: 'Static facts about your business' },
  { value: 'preference', label: 'Preference', description: 'How you like things done' },
  { value: 'customer', label: 'Customer', description: 'Facts about specific customers' },
  { value: 'job_history', label: 'Job history', description: 'Outcomes of past jobs' },
  { value: 'fact', label: 'Fact', description: 'Other durable facts' },
]

const KIND_TONE: Record<MemoryKind, 'neutral' | 'success' | 'warning' | 'info'> = {
  profile: 'info',
  preference: 'success',
  customer: 'neutral',
  job_history: 'warning',
  fact: 'neutral',
}

export function MemoryPage() {
  const qc = useQueryClient()
  const { data: memories = [], isLoading } = useQuery({
    queryKey: ['memories'],
    queryFn: () => memoriesApi.list(),
  })

  const [newContent, setNewContent] = useState('')
  const [newKind, setNewKind] = useState<MemoryKind>('profile')
  const [newImportance, setNewImportance] = useState(0.6)
  const [adding, setAdding] = useState(false)

  const createMut = useMutation({
    mutationFn: () =>
      memoriesApi.create({ content: newContent.trim(), kind: newKind, importance: newImportance }),
    onSuccess: () => {
      setNewContent('')
      setAdding(false)
      qc.invalidateQueries({ queryKey: ['memories'] })
    },
  })

  const deleteMut = useMutation({
    mutationFn: (id: number) => memoriesApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['memories'] }),
  })

  const grouped = KINDS.map(k => ({
    ...k,
    items: memories.filter((m: AgentMemory) => m.kind === k.value),
  }))

  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-[color:var(--border)] bg-[color:var(--surface)] p-5">
        <div className="flex items-start gap-3">
          <Brain className="h-5 w-5 mt-0.5 text-[color:var(--accent)]" />
          <div className="flex-1">
            <h2 className="text-base font-semibold text-[color:var(--ink)]">AI Memory</h2>
            <p className="text-sm text-[color:var(--muted-ink)] mt-1">
              Things the AI has learned about you and your business. These get pulled into
              every chat for context. You can add, edit, or delete them at any time.
            </p>
          </div>
        </div>
      </div>

      <div className="rounded-lg border border-[color:var(--border)] bg-[color:var(--surface)] p-5">
        {!adding ? (
          <Button onClick={() => setAdding(true)}>
            <Plus className="h-4 w-4 mr-1.5" />
            Add memory
          </Button>
        ) : (
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-[color:var(--muted-ink)] mb-1">
                Memory content
              </label>
              <Input
                value={newContent}
                onChange={e => setNewContent(e.target.value)}
                placeholder="e.g. My standard truck stock includes 1/2 in PEX and Sharkbite fittings"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-[color:var(--muted-ink)] mb-1">
                  Kind
                </label>
                <select
                  value={newKind}
                  onChange={e => setNewKind(e.target.value as MemoryKind)}
                  className="w-full rounded-md border border-[color:var(--border)] bg-[color:var(--surface)] px-3 py-2 text-sm"
                >
                  {KINDS.map(k => (
                    <option key={k.value} value={k.value}>{k.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-[color:var(--muted-ink)] mb-1">
                  Importance: {newImportance.toFixed(1)}
                </label>
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.1}
                  value={newImportance}
                  onChange={e => setNewImportance(parseFloat(e.target.value))}
                  className="w-full"
                />
              </div>
            </div>
            <div className="flex gap-2">
              <Button
                onClick={() => createMut.mutate()}
                disabled={!newContent.trim() || createMut.isPending}
              >
                <Sparkles className="h-4 w-4 mr-1.5" />
                Save
              </Button>
              <Button variant="ghost" onClick={() => { setAdding(false); setNewContent('') }}>
                Cancel
              </Button>
            </div>
          </div>
        )}
      </div>

      {isLoading ? (
        <p className="text-sm text-[color:var(--muted-ink)]">Loading memories…</p>
      ) : memories.length === 0 ? (
        <div className="rounded-lg border border-dashed border-[color:var(--border)] p-8 text-center">
          <Brain className="h-8 w-8 text-[color:var(--muted-ink)] mx-auto mb-2" />
          <p className="text-sm text-[color:var(--muted-ink)]">
            No memories yet. The AI will learn over time, or you can add facts manually above.
          </p>
        </div>
      ) : (
        <div className="space-y-5">
          {grouped.map(group => (
            group.items.length > 0 && (
              <section key={group.value}>
                <div className="flex items-baseline justify-between mb-2">
                  <h3 className="text-sm font-semibold text-[color:var(--ink)]">{group.label}</h3>
                  <span className="text-xs text-[color:var(--muted-ink)]">{group.description}</span>
                </div>
                <ul className="space-y-2">
                  {group.items.map((m: AgentMemory) => (
                    <li
                      key={m.id}
                      className="flex items-start gap-3 rounded-md border border-[color:var(--border)] bg-[color:var(--surface)] p-3"
                    >
                      <Badge variant={KIND_TONE[m.kind]} className="shrink-0">
                        {Math.round(m.importance * 100)}%
                      </Badge>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-[color:var(--ink)]">{m.content}</p>
                        {m.metadata && (m.metadata as Record<string, unknown>)?.extracted ? (
                          <p className="text-[11px] text-[color:var(--muted-ink)] mt-1">
                            Auto-extracted from chat
                          </p>
                        ) : null}
                      </div>
                      <button
                        onClick={() => deleteMut.mutate(m.id)}
                        className="text-[color:var(--muted-ink)] hover:text-red-600 transition-colors"
                        aria-label="Delete memory"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </li>
                  ))}
                </ul>
              </section>
            )
          ))}
        </div>
      )}
    </div>
  )
}
