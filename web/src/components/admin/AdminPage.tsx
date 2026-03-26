'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Save, RefreshCw, Wrench, DollarSign, BarChart3, AlertCircle } from 'lucide-react'
import { cn } from '@/lib/utils'
import axios from 'axios'

const API = process.env.NEXT_PUBLIC_API_URL + '/api/v1'

interface LaborTemplate {
  code: string; name: string; category: string; base_hours: number;
  lead_rate: number; helper_required: boolean; disposal_hours: number
}
interface MarkupRule {
  job_type: string; materials_markup_pct: number; misc_disposal_flat: number
}
interface Stats {
  total_estimates: number; avg_estimate_value: number;
  labor_templates_count: number; canonical_items_count: number
}

const TABS = [
  { id: 'labor', label: 'Labor Templates', icon: Wrench },
  { id: 'markup', label: 'Markup Rules', icon: DollarSign },
  { id: 'stats', label: 'Stats', icon: BarChart3 },
]

const CAT_CLASS: Record<string, string> = {
  service: 'badge-service',
  construction: 'badge-construction',
  commercial: 'badge-commercial',
}

export function AdminPage() {
  const [tab, setTab] = useState('labor')
  const [templates, setTemplates] = useState<LaborTemplate[]>([])
  const [markupRules, setMarkupRules] = useState<MarkupRule[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saveOk, setSaveOk] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (tab === 'labor') fetchTemplates()
    else if (tab === 'markup') fetchMarkup()
    else if (tab === 'stats') fetchStats()
  }, [tab])

  const fetchTemplates = async () => {
    setLoading(true); setError(null)
    try {
      const res = await axios.get(`${API}/admin/labor-templates`)
      setTemplates(res.data?.templates ?? res.data ?? [])
    } catch { setError('Failed to load templates') }
    finally { setLoading(false) }
  }

  const fetchMarkup = async () => {
    setLoading(true); setError(null)
    try {
      const res = await axios.get(`${API}/admin/markup-rules`)
      const rules = (res.data ?? []).map((r: any) => ({
        job_type: r.job_type,
        materials_markup_pct: Math.round((r.materials_markup_pct ?? 0) * 100),
        misc_disposal_flat: r.misc_flat ?? r.misc_disposal_flat ?? 0,
      }))
      setMarkupRules(rules)
    } catch { setError('Failed to load markup rules') }
    finally { setLoading(false) }
  }

  const fetchStats = async () => {
    setLoading(true); setError(null)
    try {
      const res = await axios.get(`${API}/admin/stats`)
      const d = res.data
      setStats({
        total_estimates: d.total_estimates ?? 0,
        avg_estimate_value: d.avg_estimate_value ?? 0,
        labor_templates_count: d.labor_templates_count ?? d.labor_templates ?? 0,
        canonical_items_count: d.canonical_items_count ?? d.canonical_items ?? 0,
      })
    } catch { setError('Failed to load stats') }
    finally { setLoading(false) }
  }

  const saveMarkup = async () => {
    setSaving(true)
    try {
      await Promise.all(markupRules.map(r =>
        axios.put(`${API}/admin/markup-rules/${r.job_type}`, {
          materials_markup_pct: r.materials_markup_pct / 100,
          misc_flat: r.misc_disposal_flat,
        })
      ))
      setSaveOk(true)
      setTimeout(() => setSaveOk(false), 3000)
    } catch { alert('Save failed') }
    finally { setSaving(false) }
  }

  const updateMarkup = (jobType: string, field: keyof MarkupRule, value: number) => {
    setMarkupRules(prev => prev.map(r => r.job_type === jobType ? { ...r, [field]: value } : r))
  }

  return (
    <div className="min-h-full bg-[#0a0a0a]">
      {/* Tab bar */}
      <div className="bg-black/40 backdrop-blur-xl border-b border-white/5 sticky top-0 z-10">
        <div className="flex overflow-x-auto scrollbar-hide max-w-4xl mx-auto">
          {TABS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              className={cn(
                'flex items-center gap-2 px-5 py-4 text-sm font-semibold whitespace-nowrap border-b-2 transition-colors',
                tab === id
                  ? 'border-blue-500 text-blue-400'
                  : 'border-transparent text-zinc-500 hover:text-zinc-300'
              )}
            >
              <Icon size={16} />
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-4">
        {error && (
          <div className="mb-4 flex items-center gap-2 bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3 text-sm text-red-400">
            <AlertCircle size={16} className="shrink-0" />
            {error}
            <button onClick={() => setError(null)} className="ml-auto text-red-400 hover:text-red-300">x</button>
          </div>
        )}

        {/* Labor Templates tab */}
        {tab === 'labor' && (
          loading ? (
            <div className="space-y-2">
              {[1,2,3,4,5].map(i => <div key={i} className="card p-4 skeleton h-16 rounded-2xl" />)}
            </div>
          ) : (
            <>
              {/* Mobile: cards */}
              <div className="space-y-2.5 lg:hidden">
                {templates.map((t, i) => (
                  <motion.div
                    key={t.code}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.2, delay: i * 0.03 }}
                    className="card p-4"
                  >
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <div>
                        <div className="text-sm font-bold text-white">{t.name}</div>
                        <div className="font-mono text-[11px] text-zinc-500 mt-0.5">{t.code}</div>
                      </div>
                      <span className={cn('badge text-[11px]', CAT_CLASS[t.category] ?? 'badge-service')}>
                        {t.category}
                      </span>
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-center">
                      <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl py-2">
                        <div className="text-xs text-zinc-500">Base Hours</div>
                        <div className="text-sm font-bold text-white">{t.base_hours}h</div>
                      </div>
                      <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl py-2">
                        <div className="text-xs text-zinc-500">Lead Rate</div>
                        <div className="text-sm font-bold text-white">${t.lead_rate}/hr</div>
                      </div>
                      <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl py-2">
                        <div className="text-xs text-zinc-500">Helper</div>
                        <div className="text-sm font-bold text-white">{t.helper_required ? 'Yes' : 'No'}</div>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>

              {/* Desktop: table */}
              <div className="hidden lg:block card overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-white/5 bg-white/[0.02]">
                      {['Code', 'Name', 'Category', 'Base Hrs', 'Lead Rate', 'Helper', 'Disposal Hrs'].map(h => (
                        <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-zinc-500 uppercase tracking-wider">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {templates.map((t, i) => (
                      <motion.tr
                        key={t.code}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ duration: 0.15, delay: i * 0.02 }}
                        className="hover:bg-white/[0.03] transition-colors"
                      >
                        <td className="px-4 py-3 font-mono text-xs text-zinc-500">{t.code}</td>
                        <td className="px-4 py-3 font-medium text-white">{t.name}</td>
                        <td className="px-4 py-3">
                          <span className={cn('badge', CAT_CLASS[t.category] ?? 'badge-service')}>{t.category}</span>
                        </td>
                        <td className="px-4 py-3 text-zinc-300">{t.base_hours}h</td>
                        <td className="px-4 py-3 text-zinc-300">${t.lead_rate}/hr</td>
                        <td className="px-4 py-3">
                          <span className={cn('badge', t.helper_required ? 'badge-construction' : 'bg-white/5 text-zinc-500 border border-white/10')}>
                            {t.helper_required ? 'Yes' : 'No'}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-zinc-300">{t.disposal_hours}h</td>
                      </motion.tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )
        )}

        {/* Markup Rules tab */}
        {tab === 'markup' && (
          loading ? (
            <div className="space-y-3">
              {[1,2,3].map(i => <div key={i} className="card p-6 skeleton h-32 rounded-2xl" />)}
            </div>
          ) : (
            <div className="space-y-3">
              {saveOk && (
                <div className="flex items-center gap-2 bg-emerald-500/10 border border-emerald-500/20 rounded-xl px-4 py-3 text-sm text-emerald-400">
                  Markup rules saved successfully
                </div>
              )}
              {markupRules.map((rule, i) => (
                <motion.div
                  key={rule.job_type}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.2, delay: i * 0.05 }}
                  className="card p-5"
                >
                  <div className="flex items-center gap-2 mb-4">
                    <span className={cn('badge', CAT_CLASS[rule.job_type] ?? 'badge-service')}>
                      {rule.job_type}
                    </span>
                    <span className="text-sm font-semibold text-zinc-300 capitalize">
                      {rule.job_type} Jobs
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-semibold text-zinc-500 mb-1.5">Materials Markup %</label>
                      <div className="relative">
                        <input
                          type="number"
                          className="input pr-8 text-sm"
                          value={rule.materials_markup_pct}
                          onChange={e => updateMarkup(rule.job_type, 'materials_markup_pct', parseFloat(e.target.value))}
                          step="1"
                          min="0"
                          max="100"
                        />
                        <span className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 text-sm font-medium">%</span>
                      </div>
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-zinc-500 mb-1.5">Misc / Disposal Flat</label>
                      <div className="relative">
                        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500 text-sm font-medium">$</span>
                        <input
                          type="number"
                          className="input pl-7 text-sm"
                          value={rule.misc_disposal_flat}
                          onChange={e => updateMarkup(rule.job_type, 'misc_disposal_flat', parseFloat(e.target.value))}
                          step="5"
                          min="0"
                        />
                      </div>
                    </div>
                  </div>
                </motion.div>
              ))}
              {markupRules.length > 0 && (
                <motion.button
                  onClick={saveMarkup}
                  disabled={saving}
                  whileTap={{ scale: 0.97 }}
                  className="btn-primary w-full gap-2"
                >
                  {saving ? <RefreshCw size={16} className="animate-spin" /> : <Save size={16} />}
                  {saving ? 'Saving...' : 'Save Markup Rules'}
                </motion.button>
              )}
            </div>
          )
        )}

        {/* Stats tab */}
        {tab === 'stats' && (
          loading ? (
            <div className="grid grid-cols-2 gap-3">
              {[1,2,3,4].map(i => <div key={i} className="card p-5 skeleton h-24 rounded-2xl" />)}
            </div>
          ) : stats ? (
            <div className="grid grid-cols-2 gap-3">
              {[
                { label: 'Total Estimates', value: stats.total_estimates?.toString() ?? '0', icon: BarChart3, color: 'bg-blue-500/10 text-blue-400 border border-blue-500/20' },
                { label: 'Avg Value', value: `$${Math.round(stats.avg_estimate_value ?? 0).toLocaleString()}`, icon: DollarSign, color: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' },
                { label: 'Labor Templates', value: stats.labor_templates_count?.toString() ?? '0', icon: Wrench, color: 'bg-violet-500/10 text-violet-400 border border-violet-500/20' },
                { label: 'Catalog Items', value: stats.canonical_items_count?.toString() ?? '0', icon: RefreshCw, color: 'bg-orange-500/10 text-orange-400 border border-orange-500/20' },
              ].map(({ label, value, icon: Icon, color }, i) => (
                <motion.div
                  key={label}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.2, delay: i * 0.05 }}
                  className="card p-4 flex flex-col gap-3"
                >
                  <div className={cn('w-10 h-10 rounded-xl flex items-center justify-center', color)}>
                    <Icon size={18} />
                  </div>
                  <div>
                    <div className="text-2xl font-extrabold text-white">{value}</div>
                    <div className="text-xs text-zinc-500 font-medium mt-0.5">{label}</div>
                  </div>
                </motion.div>
              ))}
            </div>
          ) : (
            <div className="card p-8 text-center">
              <p className="text-zinc-400 text-sm mb-3">Stats unavailable</p>
              <button onClick={fetchStats} className="btn-secondary text-sm mx-auto">Retry</button>
            </div>
          )
        )}
      </div>
    </div>
  )
}
