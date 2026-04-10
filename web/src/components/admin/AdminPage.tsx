'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Save, RefreshCw, Wrench, DollarSign, BarChart3, Package } from 'lucide-react'
import { cn } from '@/lib/utils'
import { api } from '@/lib/api'
import { useToast } from '@/components/ui/Toast'
import { PageIntro } from '@/components/layout/PageIntro'
import { Badge } from '@/components/ui/Badge'
import { Skeleton } from '@/components/ui/Skeleton'
import { ErrorState } from '@/components/ui/ErrorState'

interface LaborTemplate {
  code: string; name: string; category: string; base_hours: number
  lead_rate: number; helper_required: boolean; disposal_hours: number
}
interface MarkupRule { job_type: string; materials_markup_pct: number; misc_disposal_flat: number }
interface MarkupRuleResponse { job_type: string; materials_markup_pct?: number; misc_flat?: number; misc_disposal_flat?: number }
interface Stats { total_estimates: number; avg_estimate_value: number; labor_templates_count: number; canonical_items_count: number }

const TABS = [
  { id: 'labor', label: 'Labor Templates', icon: Wrench },
  { id: 'markup', label: 'Markup Rules', icon: DollarSign },
  { id: 'stats', label: 'Stats', icon: BarChart3 },
]

const CAT_VARIANT: Record<string, 'success' | 'warning' | 'info' | 'accent' | 'neutral'> = {
  service: 'info',
  construction: 'warning',
  commercial: 'accent',
}

export function AdminPage() {
  const toast = useToast()
  const [tab, setTab] = useState('labor')
  const [templates, setTemplates] = useState<LaborTemplate[]>([])
  const [markupRules, setMarkupRules] = useState<MarkupRule[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saveOk, setSaveOk] = useState(false)
  const [confirmSave, setConfirmSave] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (tab === 'labor') {
      void fetchTemplates()
    } else if (tab === 'markup') {
      void fetchMarkup()
    } else if (tab === 'stats') {
      void fetchStats()
    }
  }, [tab])

  const fetchTemplates = async () => {
    setLoading(true); setError(null)
    try {
      const res = await api.get('/admin/labor-templates')
      setTemplates(res.data?.templates ?? res.data ?? [])
    } catch {
      setError('Failed to load templates')
    } finally {
      setLoading(false)
    }
  }

  const fetchMarkup = async () => {
    setLoading(true); setError(null)
    try {
      const res = await api.get('/admin/markup-rules')
      const rules = (res.data ?? []).map((r: MarkupRuleResponse) => ({
        job_type: r.job_type,
        materials_markup_pct: Math.round((r.materials_markup_pct ?? 0) * 100),
        misc_disposal_flat: r.misc_flat ?? r.misc_disposal_flat ?? 0,
      }))
      setMarkupRules(rules)
    } catch {
      setError('Failed to load markup rules')
    } finally {
      setLoading(false)
    }
  }

  const fetchStats = async () => {
    setLoading(true); setError(null)
    try {
      const res = await api.get('/admin/stats')
      const d = res.data
      setStats({
        total_estimates: d.total_estimates ?? 0,
        avg_estimate_value: d.avg_estimate_value ?? 0,
        labor_templates_count: d.labor_templates_count ?? d.labor_templates ?? 0,
        canonical_items_count: d.canonical_items_count ?? d.canonical_items ?? 0,
      })
    } catch {
      setError('Failed to load stats')
    } finally {
      setLoading(false)
    }
  }

  const saveMarkup = async () => {
    setConfirmSave(false)
    setSaving(true)
    try {
      await Promise.all(markupRules.map(r =>
        api.put(`/admin/markup-rules/${r.job_type}`, {
          materials_markup_pct: r.materials_markup_pct / 100,
          misc_flat: r.misc_disposal_flat,
        })
      ))
      toast.success('Markup rules saved')
      setSaveOk(true)
      setTimeout(() => setSaveOk(false), 3000)
    } catch {
      setError('Failed to save markup rules. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  const updateMarkup = (jobType: string, field: keyof MarkupRule, rawValue: number) => {
    const value = field === 'materials_markup_pct'
      ? Math.min(200, Math.max(0, rawValue))
      : Math.min(500, Math.max(0, rawValue))
    setMarkupRules(prev => prev.map(r => r.job_type === jobType ? { ...r, [field]: value } : r))
  }

  const refreshCurrentTab = () => {
    if (tab === 'labor') {
      void fetchTemplates()
      return
    }
    if (tab === 'markup') {
      void fetchMarkup()
      return
    }
    void fetchStats()
  }

  return (
    <div className="min-h-full">
      <div className="mx-auto w-full max-w-4xl px-4 py-5 sm:px-6 lg:px-8">
        <PageIntro
          eyebrow="Admin Controls"
          title="Tune pricing rules and template baselines."
          description="Manage labor templates, markup settings, and estimator health stats from one control surface."
          actions={(
            <button
              onClick={refreshCurrentTab}
              className="btn-secondary min-h-0 px-3 py-2"
              disabled={loading}
            >
              <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
              <span className="hidden sm:inline">Refresh</span>
            </button>
          )}
        >
          <div className="flex flex-wrap gap-1.5">
            {TABS.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setTab(id)}
                className={cn(
                  'inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wider transition-colors',
                  tab === id
                    ? 'border-[color:var(--accent)] bg-[color:var(--accent-soft)] text-[color:var(--accent-strong)]'
                    : 'border-[color:var(--line)] bg-[color:var(--panel)] text-[color:var(--muted-ink)] hover:bg-[color:var(--panel-strong)] hover:text-[color:var(--ink)]',
                )}
              >
                <Icon size={13} />
                {label}
              </button>
            ))}
          </div>
        </PageIntro>

        <div className="mt-4">
          {error && (
            <ErrorState
              message={error}
              onRetry={() => { setError(null); refreshCurrentTab() }}
              className="mb-4"
            />
          )}

          {tab === 'labor' && (
            loading
              ? <Skeleton variant="card" count={5} className="h-16 rounded-2xl" />
              : <>
                  <div className="space-y-2.5 lg:hidden">
                    {templates.map((t, i) => (
                      <motion.div
                        key={t.code}
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.18, delay: i * 0.03 }}
                        className="card p-4 hover:shadow-lg transition-all"
                      >
                        <div className="mb-3 flex items-start justify-between gap-2">
                          <div>
                            <div className="text-sm font-bold text-[color:var(--ink)]">{t.name}</div>
                            <div className="mt-0.5 font-mono text-[10px] text-[color:var(--muted-ink)]">{t.code}</div>
                          </div>
                          <Badge variant={CAT_VARIANT[t.category] ?? 'neutral'}>{t.category}</Badge>
                        </div>
                        <div className="grid grid-cols-3 gap-2">
                          {[
                            { label: 'Base Hrs', value: `${t.base_hours}h` },
                            { label: 'Lead Rate', value: `$${t.lead_rate}/h` },
                            { label: 'Helper', value: t.helper_required ? 'Yes' : 'No' },
                          ].map(({ label, value }) => (
                            <div key={label} className="card-inset py-2 text-center">
                              <div className="text-[10px] text-[color:var(--muted-ink)]">{label}</div>
                              <div className="mt-0.5 text-xs font-bold text-[color:var(--ink)]">{value}</div>
                            </div>
                          ))}
                        </div>
                      </motion.div>
                    ))}
                  </div>

                  <div className="hidden lg:block card overflow-auto max-h-[70vh]">
                    <table className="w-full text-sm">
                      <thead className="sticky top-0 z-10">
                        <tr className="border-b border-[color:var(--line)] bg-[color:var(--panel-strong)]">
                          {['Code', 'Name', 'Category', 'Base Hrs', 'Lead Rate', 'Helper', 'Disposal'].map(h => (
                            <th key={h} className="px-4 py-3 text-left text-[10px] font-bold uppercase tracking-widest text-[color:var(--muted-ink)]">{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[color:var(--line)]">
                        {templates.map((t, i) => (
                          <motion.tr
                            key={t.code}
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            transition={{ duration: 0.12, delay: i * 0.02 }}
                            className="transition-colors hover:bg-[color:var(--panel-strong)]"
                          >
                            <td className="px-4 py-3 font-mono text-[11px] text-[color:var(--muted-ink)]">{t.code}</td>
                            <td className="px-4 py-3 font-medium text-[color:var(--ink)]">{t.name}</td>
                            <td className="px-4 py-3">
                              <Badge variant={CAT_VARIANT[t.category] ?? 'neutral'}>{t.category}</Badge>
                            </td>
                            <td className="px-4 py-3 tabular-nums text-[color:var(--muted-ink)]">{t.base_hours}h</td>
                            <td className="px-4 py-3 tabular-nums text-[color:var(--muted-ink)]">${t.lead_rate}/h</td>
                            <td className="px-4 py-3">
                              <Badge variant={t.helper_required ? 'warning' : 'neutral'}>
                                {t.helper_required ? 'Yes' : 'No'}
                              </Badge>
                            </td>
                            <td className="px-4 py-3 tabular-nums text-[color:var(--muted-ink)]">{t.disposal_hours}h</td>
                          </motion.tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </>
          )}

          {tab === 'markup' && (
            loading
              ? <Skeleton variant="card" count={3} className="h-32 rounded-2xl" />
              : <div className="space-y-3">
                  {saveOk && (
                    <div className="flex items-center gap-2 rounded-xl border border-[hsl(var(--success)/0.2)] bg-[hsl(var(--success)/0.1)] px-4 py-3 text-sm text-[hsl(var(--success))]">
                      Markup rules saved successfully
                    </div>
                  )}
                  {markupRules.map((rule, i) => (
                    <motion.div
                      key={rule.job_type}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.18, delay: i * 0.05 }}
                      className="card p-5 hover:shadow-lg transition-all"
                    >
                      <div className="mb-4 flex items-center gap-2">
                        <Badge variant={CAT_VARIANT[rule.job_type] ?? 'neutral'}>
                          {rule.job_type}
                        </Badge>
                        <span className="text-sm font-semibold capitalize text-[color:var(--ink)]">{rule.job_type} Jobs</span>
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="mb-2 block text-[11px] font-bold uppercase tracking-wider text-[color:var(--muted-ink)]">
                            Materials Markup
                          </label>
                          <div className="relative">
                            <input
                              type="number"
                              className="input pr-8 focus-visible:ring-2 focus-visible:ring-[color:var(--accent)]"
                              value={rule.materials_markup_pct}
                              onChange={e => updateMarkup(rule.job_type, 'materials_markup_pct', parseFloat(e.target.value))}
                              step="1" min="0" max="200"
                            />
                            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-bold text-[color:var(--muted-ink)]">%</span>
                          </div>
                        </div>
                        <div>
                          <label className="mb-2 block text-[11px] font-bold uppercase tracking-wider text-[color:var(--muted-ink)]">
                            Misc / Disposal Flat
                          </label>
                          <div className="relative">
                            <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-xs font-bold text-[color:var(--muted-ink)]">$</span>
                            <input
                              type="number"
                              className="input pl-7 focus-visible:ring-2 focus-visible:ring-[color:var(--accent)]"
                              value={rule.misc_disposal_flat}
                              onChange={e => updateMarkup(rule.job_type, 'misc_disposal_flat', parseFloat(e.target.value))}
                              step="5" min="0"
                            />
                          </div>
                        </div>
                      </div>
                    </motion.div>
                  ))}
                  {markupRules.length > 0 && (
                    <motion.div className="flex items-center gap-2">
                      {confirmSave ? (
                        <>
                          <span className="text-sm text-[color:var(--muted-ink)] flex-1">Save changes to all markup rules?</span>
                          <button
                            onClick={() => void saveMarkup()}
                            disabled={saving}
                            className="btn-primary disabled:opacity-50"
                          >
                            {saving ? <RefreshCw size={14} className="animate-spin" /> : <Save size={14} />}
                            {saving ? 'Saving…' : 'Confirm Save'}
                          </button>
                          <button
                            onClick={() => setConfirmSave(false)}
                            className="btn-secondary"
                          >Cancel</button>
                        </>
                      ) : (
                        <motion.button
                          onClick={() => setConfirmSave(true)}
                          whileTap={{ scale: 0.97 }}
                          className="btn-primary w-full"
                        >
                          <Save size={15} />
                          Save Markup Rules
                        </motion.button>
                      )}
                    </motion.div>
                  )}
                </div>
          )}

          {tab === 'stats' && (
            loading
              ? <div className="grid grid-cols-2 gap-3">
                  <Skeleton variant="stat-card" className="h-28 rounded-2xl" />
                  <Skeleton variant="stat-card" className="h-28 rounded-2xl" />
                  <Skeleton variant="stat-card" className="h-28 rounded-2xl" />
                  <Skeleton variant="stat-card" className="h-28 rounded-2xl" />
                </div>
              : stats
                ? <div className="grid grid-cols-2 gap-3">
                    {[
                      { label: 'Total Estimates', value: stats.total_estimates, icon: BarChart3, color: 'text-[hsl(var(--info))]', bg: 'bg-[hsl(var(--info)/0.1)] border-[hsl(var(--info)/0.2)]' },
                      { label: 'Avg Value', value: `$${Math.round(stats.avg_estimate_value ?? 0).toLocaleString()}`, icon: DollarSign, color: 'text-[hsl(var(--success))]', bg: 'bg-[hsl(var(--success)/0.1)] border-[hsl(var(--success)/0.2)]' },
                      { label: 'Labor Templates', value: stats.labor_templates_count, icon: Wrench, color: 'text-[color:var(--accent-strong)]', bg: 'bg-[color:var(--accent-soft)] border-[color:var(--accent)]/20' },
                      { label: 'Catalog Items', value: stats.canonical_items_count, icon: Package, color: 'text-[hsl(var(--warning-foreground))]', bg: 'bg-[hsl(var(--warning)/0.1)] border-[hsl(var(--warning)/0.2)]' },
                    ].map(({ label, value, icon: Icon, color, bg }, i) => (
                      <motion.div
                        key={label}
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.18, delay: i * 0.05 }}
                        className="card flex flex-col gap-4 p-5 hover:shadow-lg transition-all"
                      >
                        <div className={cn('flex h-10 w-10 items-center justify-center rounded-xl border', bg)}>
                          <Icon size={18} className={color} />
                        </div>
                        <div>
                          <div className="text-2xl font-extrabold tabular-nums text-[color:var(--ink)]">{value}</div>
                          <div className="mt-0.5 text-[11px] font-medium text-[color:var(--muted-ink)]">{label}</div>
                        </div>
                      </motion.div>
                    ))}
                  </div>
                : <ErrorState
                    message="Stats unavailable"
                    onRetry={fetchStats}
                  />
          )}
        </div>
      </div>
    </div>
  )
}
