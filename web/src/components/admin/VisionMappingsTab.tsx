'use client'

/**
 * Phase 3.5 — Admin tab for editing the photo-vision → labor-template map.
 *
 * Rows in `vision_item_mappings` override entries in the static `_ITEM_TO_TASK`
 * dict in services/photo_quote.py.  Static fallbacks are listed read-only;
 * adding/editing a row converts it into a DB-backed override.
 */

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'

type Mapping = {
  id: number | null
  item_type: string
  default_task_code: string
  problem_task_code: string | null
  enabled: boolean
  note: string | null
  source: 'db' | 'static'
}

type ListResp = { mappings: Mapping[]; valid_task_codes: string[] }

export function VisionMappingsTab() {
  const queryClient = useQueryClient()
  const { data, isLoading, error } = useQuery({
    queryKey: ['admin', 'vision-mappings'],
    queryFn: async () => (await api.get<ListResp>('/admin/vision-mappings')).data,
  })

  const [editing, setEditing] = useState<Mapping | null>(null)
  const [filter, setFilter] = useState('')

  const upsert = useMutation({
    mutationFn: async (body: Partial<Mapping>) => (await api.post('/admin/vision-mappings', body)).data,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['admin', 'vision-mappings'] })
      setEditing(null)
    },
  })

  const remove = useMutation({
    mutationFn: async (item_type: string) => (await api.delete(`/admin/vision-mappings/${encodeURIComponent(item_type)}`)).data,
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['admin', 'vision-mappings'] }),
  })

  if (isLoading) return <div className="text-zinc-400 text-sm">Loading mappings…</div>
  if (error || !data) return <div className="text-red-400 text-sm">Failed to load mappings.</div>

  const visible = data.mappings.filter(m =>
    !filter ||
    m.item_type.includes(filter.toLowerCase()) ||
    m.default_task_code.toLowerCase().includes(filter.toLowerCase()),
  )

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <input
          placeholder="Filter by item type or task code…"
          value={filter}
          onChange={e => setFilter(e.target.value)}
          className="rounded-lg bg-white/[0.04] border border-white/[0.08] px-3 py-2 text-xs text-zinc-200 w-72"
        />
        <button
          onClick={() => setEditing({ id: null, item_type: '', default_task_code: '', problem_task_code: null, enabled: true, note: null, source: 'db' })}
          className="rounded-lg bg-blue-600 hover:bg-blue-500 px-3 py-2 text-xs font-semibold text-white"
        >
          + New mapping
        </button>
      </div>

      <div className="overflow-hidden rounded-xl border border-white/[0.06] bg-white/[0.02]">
        <table className="w-full text-xs">
          <thead className="bg-white/[0.03] text-left text-[11px] uppercase tracking-wider text-zinc-500">
            <tr>
              <th className="px-3 py-2">Item type</th>
              <th className="px-3 py-2">Default task code</th>
              <th className="px-3 py-2">Problem task code</th>
              <th className="px-3 py-2">Enabled</th>
              <th className="px-3 py-2">Source</th>
              <th className="px-3 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {visible.map(m => (
              <tr key={`${m.item_type}-${m.source}`} className="border-t border-white/[0.04]">
                <td className="px-3 py-2 font-mono text-zinc-300">{m.item_type}</td>
                <td className="px-3 py-2 text-zinc-300">{m.default_task_code}</td>
                <td className="px-3 py-2 text-zinc-400">{m.problem_task_code || '—'}</td>
                <td className="px-3 py-2">{m.enabled ? '✓' : '✗'}</td>
                <td className="px-3 py-2">
                  {m.source === 'db'
                    ? <span className="rounded bg-blue-500/20 text-blue-300 px-2 py-0.5">override</span>
                    : <span className="rounded bg-zinc-500/20 text-zinc-400 px-2 py-0.5">default</span>}
                </td>
                <td className="px-3 py-2 text-right">
                  <button onClick={() => setEditing({ ...m, source: 'db' })}
                    className="text-blue-300 hover:text-blue-200 mr-3">Edit</button>
                  {m.source === 'db' && (
                    <button onClick={() => { if (confirm(`Remove override for "${m.item_type}"?`)) void remove.mutate(m.item_type) }}
                      className="text-red-300 hover:text-red-200">Reset</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {editing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-md rounded-2xl bg-zinc-900 border border-white/[0.08] p-5 space-y-3">
            <h3 className="text-sm font-semibold text-zinc-100">
              {editing.id ? 'Edit override' : 'New mapping override'}
            </h3>

            <label className="block text-[11px] text-zinc-400">
              Item type
              <input
                disabled={!!editing.id}
                value={editing.item_type}
                onChange={e => setEditing({ ...editing, item_type: e.target.value.toLowerCase().trim() })}
                placeholder="e.g. kitchen_faucet"
                className="mt-1 w-full rounded-lg bg-white/[0.04] border border-white/[0.08] px-3 py-2 text-xs text-zinc-200 disabled:opacity-60"
              />
            </label>

            <label className="block text-[11px] text-zinc-400">
              Default task code
              <input
                list="vision-task-codes"
                value={editing.default_task_code}
                onChange={e => setEditing({ ...editing, default_task_code: e.target.value.toUpperCase() })}
                className="mt-1 w-full rounded-lg bg-white/[0.04] border border-white/[0.08] px-3 py-2 text-xs text-zinc-200"
              />
            </label>

            <label className="block text-[11px] text-zinc-400">
              Problem task code (used when condition is leaking/broken/corroded)
              <input
                list="vision-task-codes"
                value={editing.problem_task_code || ''}
                onChange={e => setEditing({ ...editing, problem_task_code: e.target.value.toUpperCase() || null })}
                className="mt-1 w-full rounded-lg bg-white/[0.04] border border-white/[0.08] px-3 py-2 text-xs text-zinc-200"
              />
            </label>

            <datalist id="vision-task-codes">
              {data.valid_task_codes.map(c => <option key={c} value={c} />)}
            </datalist>

            <label className="block text-[11px] text-zinc-400">
              Note
              <textarea
                value={editing.note || ''}
                onChange={e => setEditing({ ...editing, note: e.target.value || null })}
                rows={2}
                className="mt-1 w-full rounded-lg bg-white/[0.04] border border-white/[0.08] px-3 py-2 text-xs text-zinc-200"
              />
            </label>

            <label className="flex items-center gap-2 text-[12px] text-zinc-300">
              <input type="checkbox" checked={editing.enabled} onChange={e => setEditing({ ...editing, enabled: e.target.checked })} />
              Enabled
            </label>

            {upsert.isError && (
              <div className="text-xs text-red-400">
                {(upsert.error as Error)?.message || 'Save failed'}
              </div>
            )}

            <div className="flex justify-end gap-2 pt-1">
              <button onClick={() => setEditing(null)}
                className="rounded-lg bg-white/[0.05] hover:bg-white/[0.08] px-3 py-2 text-xs text-zinc-300">
                Cancel
              </button>
              <button
                disabled={!editing.item_type || !editing.default_task_code || upsert.isPending}
                onClick={() => upsert.mutate({
                  item_type: editing.item_type,
                  default_task_code: editing.default_task_code,
                  problem_task_code: editing.problem_task_code || undefined,
                  enabled: editing.enabled,
                  note: editing.note || undefined,
                })}
                className="rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 px-3 py-2 text-xs font-semibold text-white">
                {upsert.isPending ? 'Saving…' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
