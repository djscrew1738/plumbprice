'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Flag, Plus, Trash2 } from 'lucide-react'
import { adminApi, type FlagRow } from '@/lib/api'
import { useToast } from '@/components/ui/Toast'

const ADMIN_FLAGS_KEY = ['admin', 'flags'] as const

export function FeatureFlagsTab() {
  const toast = useToast()
  const qc = useQueryClient()
  const [newKey, setNewKey] = useState('')
  const [newDesc, setNewDesc] = useState('')

  const { data: flags = [], isLoading, isError } = useQuery({
    queryKey: ADMIN_FLAGS_KEY,
    queryFn: async () => (await adminApi.listFlags()).data,
    staleTime: 30_000,
  })

  const invalidate = () => {
    void qc.invalidateQueries({ queryKey: ADMIN_FLAGS_KEY })
    void qc.invalidateQueries({ queryKey: ['feature-flags'] })
  }

  const toggle = useMutation({
    mutationFn: ({ key, enabled }: { key: string; enabled: boolean }) =>
      adminApi.toggleFlag(key, enabled),
    onSuccess: (_d, vars) => {
      toast.success(`Flag ${vars.key} ${vars.enabled ? 'enabled' : 'disabled'}`)
      invalidate()
    },
    onError: () => toast.error('Failed to update flag'),
  })

  const upsert = useMutation({
    mutationFn: (body: { key: string; enabled: boolean; description?: string | null }) =>
      adminApi.upsertFlag(body),
    onSuccess: () => {
      toast.success('Flag created')
      setNewKey('')
      setNewDesc('')
      invalidate()
    },
    onError: () => toast.error('Failed to create flag (key must be lowercase a-z0-9_)'),
  })

  const remove = useMutation({
    mutationFn: (key: string) => adminApi.deleteFlag(key),
    onSuccess: () => {
      toast.success('Flag deleted')
      invalidate()
    },
    onError: () => toast.error('Failed to delete flag'),
  })

  if (isLoading) {
    return <div className="p-6 text-sm text-zinc-400">Loading flags…</div>
  }
  if (isError) {
    return <div className="p-6 text-sm text-rose-400">Failed to load flags.</div>
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="flex items-center gap-2 text-lg font-semibold text-[color:var(--ink)]">
          <Flag className="h-5 w-5 text-[color:var(--accent-strong)]" />
          Feature flags
        </h2>
        <p className="mt-1 text-sm text-zinc-400">
          Toggle experimental capabilities at runtime. Changes take effect immediately for new
          page loads; in-flight pages refetch within a minute.
        </p>
      </div>

      <div className="rounded-xl border border-zinc-800 bg-zinc-950/50">
        <table className="w-full text-sm">
          <thead className="border-b border-zinc-800 text-left text-xs uppercase tracking-wider text-zinc-500">
            <tr>
              <th className="px-4 py-3">Key</th>
              <th className="px-4 py-3">Description</th>
              <th className="px-4 py-3">Updated</th>
              <th className="px-4 py-3 text-right">State</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800">
            {flags.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-sm text-zinc-500">
                  No flags yet. Create one below.
                </td>
              </tr>
            )}
            {flags.map((f: FlagRow) => (
              <tr key={f.key}>
                <td className="px-4 py-3 font-mono text-xs text-[color:var(--ink)]">{f.key}</td>
                <td className="px-4 py-3 text-zinc-300">{f.description ?? '—'}</td>
                <td className="px-4 py-3 text-xs text-zinc-500">
                  {f.updated_at ? new Date(f.updated_at).toLocaleString() : '—'}
                </td>
                <td className="px-4 py-3 text-right">
                  <label className="inline-flex cursor-pointer items-center gap-2">
                    <input
                      type="checkbox"
                      checked={f.enabled}
                      disabled={toggle.isPending}
                      onChange={(e) => toggle.mutate({ key: f.key, enabled: e.target.checked })}
                      className="h-4 w-4 rounded border-zinc-700 bg-zinc-900 text-[color:var(--accent-strong)]"
                    />
                    <span className={f.enabled ? 'text-emerald-400' : 'text-zinc-500'}>
                      {f.enabled ? 'on' : 'off'}
                    </span>
                  </label>
                </td>
                <td className="px-4 py-3 text-right">
                  <button
                    type="button"
                    onClick={() => {
                      if (confirm(`Delete flag "${f.key}"?`)) remove.mutate(f.key)
                    }}
                    className="rounded p-1 text-zinc-500 hover:bg-zinc-800 hover:text-rose-400"
                    title="Delete flag"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="rounded-xl border border-zinc-800 bg-zinc-950/50 p-4">
        <h3 className="text-sm font-semibold text-[color:var(--ink)]">New flag</h3>
        <div className="mt-3 grid gap-3 sm:grid-cols-[1fr_2fr_auto]">
          <input
            value={newKey}
            onChange={(e) => setNewKey(e.target.value.toLowerCase())}
            placeholder="key_name"
            className="rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-[color:var(--ink)] placeholder-zinc-500"
          />
          <input
            value={newDesc}
            onChange={(e) => setNewDesc(e.target.value)}
            placeholder="What does this flag control?"
            className="rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-[color:var(--ink)] placeholder-zinc-500"
          />
          <button
            type="button"
            disabled={!newKey || upsert.isPending}
            onClick={() =>
              upsert.mutate({ key: newKey.trim(), enabled: false, description: newDesc.trim() || null })
            }
            className="inline-flex items-center justify-center gap-1 rounded-lg bg-[color:var(--accent-strong)] px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
          >
            <Plus className="h-4 w-4" /> Add
          </button>
        </div>
        <p className="mt-2 text-xs text-zinc-500">
          Keys must match <code className="text-zinc-400">^[a-z][a-z0-9_]*$</code>. New flags start
          disabled.
        </p>
      </div>
    </div>
  )
}
