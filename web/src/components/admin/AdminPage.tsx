'use client'

import { useState, useEffect, useCallback } from 'react'
import { RefreshCw, Wrench, DollarSign, BarChart3, Package } from 'lucide-react'
import { api, adminApi, type CanonicalItem, type CanonicalItemSupplier } from '@/lib/api'
import { useToast } from '@/components/ui/Toast'
import { PageIntro } from '@/components/layout/PageIntro'
import { ErrorState } from '@/components/ui/ErrorState'
import { TabsRoot, TabsList, TabsTrigger, TabsContent } from '@/components/ui/Tabs'
import { LaborTemplatesTab } from './LaborTemplatesTab'
import { MarkupRulesTab } from './MarkupRulesTab'
import { ItemPricesTab } from './ItemPricesTab'
import { StatsTab } from './StatsTab'

interface LaborTemplate {
  code: string; name: string; category: string; base_hours: number
  lead_rate: number; helper_required: boolean; disposal_hours: number
}
interface MarkupRule { job_type: string; materials_markup_pct: number; misc_disposal_flat: number }
interface MarkupRuleResponse { job_type: string; materials_markup_pct?: number; misc_flat?: number; misc_disposal_flat?: number }
interface Stats { total_estimates: number; avg_estimate_value: number; labor_templates_count: number; canonical_items_count: number }

const SUPPLIERS = ['ferguson', 'moore_supply', 'apex'] as const
type SupplierSlug = typeof SUPPLIERS[number]

type EditValues = Record<SupplierSlug, Partial<CanonicalItemSupplier>>

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
  const [canonicalItems, setCanonicalItems] = useState<CanonicalItem[]>([])
  const [priceSearch, setPriceSearch] = useState('')
  const [editItem, setEditItem] = useState<CanonicalItem | null>(null)
  const [editValues, setEditValues] = useState<EditValues>({} as EditValues)
  const [editSaving, setEditSaving] = useState(false)

  useEffect(() => {
    if (tab === 'labor') {
      void fetchTemplates()
    } else if (tab === 'markup') {
      void fetchMarkup()
    } else if (tab === 'prices') {
      void fetchCanonicalItems()
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

  const fetchCanonicalItems = async () => {
    setLoading(true); setError(null)
    try {
      const res = await adminApi.listCanonicalItems()
      setCanonicalItems(res.data?.items ?? [])
    } catch {
      setError('Failed to load item prices')
    } finally {
      setLoading(false)
    }
  }

  const openEditItem = useCallback((item: CanonicalItem) => {
    setEditItem(item)
    const vals = {} as EditValues
    for (const slug of SUPPLIERS) {
      const s = item.suppliers[slug]
      vals[slug] = s ? { name: s.name, cost: s.cost, unit: s.unit, sku: s.sku ?? '' } : { name: '', cost: 0, unit: 'ea', sku: '' }
    }
    setEditValues(vals)
  }, [])

  const saveEditItem = useCallback(async () => {
    if (!editItem) return
    setEditSaving(true)
    try {
      await Promise.all(
        SUPPLIERS
          .filter(slug => editValues[slug]?.name && (editValues[slug]?.cost ?? 0) > 0)
          .map(slug => adminApi.updateCanonicalItem(editItem.canonical_item, slug, {
            name: editValues[slug].name!,
            cost: Number(editValues[slug].cost),
            unit: editValues[slug].unit ?? 'ea',
            sku: editValues[slug].sku || undefined,
          }))
      )
      toast.success('Prices updated')
      setEditItem(null)
      void fetchCanonicalItems()
    } catch {
      toast.error('Could not save prices', 'Please try again.')
    } finally {
      setEditSaving(false)
    }
  }, [editItem, editValues, toast])

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
    if (tab === 'labor') { void fetchTemplates(); return }
    if (tab === 'markup') { void fetchMarkup(); return }
    if (tab === 'prices') { void fetchCanonicalItems(); return }
    void fetchStats()
  }

  const handleEditValueChange = useCallback((slug: SupplierSlug, field: string, value: string | number) => {
    setEditValues(prev => ({ ...prev, [slug]: { ...prev[slug], [field]: value } }))
  }, [])

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
              aria-label="Refresh"
            >
              <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
              <span className="hidden sm:inline">Refresh</span>
            </button>
          )}
        />

        <TabsRoot value={tab} onChange={setTab} className="mt-4">
          <TabsList>
            <TabsTrigger value="labor" icon={Wrench}>Labor Templates</TabsTrigger>
            <TabsTrigger value="markup" icon={DollarSign}>Markup Rules</TabsTrigger>
            <TabsTrigger value="prices" icon={Package}>Item Prices</TabsTrigger>
            <TabsTrigger value="stats" icon={BarChart3}>Stats</TabsTrigger>
          </TabsList>

          <div className="mt-4">
            {error && (
              <ErrorState
                message={error}
                onRetry={() => { setError(null); refreshCurrentTab() }}
                className="mb-4"
              />
            )}

            <TabsContent value="labor">
              <LaborTemplatesTab templates={templates} loading={loading} />
            </TabsContent>

            <TabsContent value="markup">
              <MarkupRulesTab
                markupRules={markupRules}
                loading={loading}
                saving={saving}
                saveOk={saveOk}
                confirmSave={confirmSave}
                onUpdateMarkup={updateMarkup}
                onSetConfirmSave={setConfirmSave}
                onSaveMarkup={() => void saveMarkup()}
              />
            </TabsContent>

            <TabsContent value="prices">
              <ItemPricesTab
                canonicalItems={canonicalItems}
                loading={loading}
                priceSearch={priceSearch}
                onPriceSearchChange={setPriceSearch}
                editItem={editItem}
                editValues={editValues}
                editSaving={editSaving}
                onOpenEditItem={openEditItem}
                onCloseEditItem={() => setEditItem(null)}
                onEditValueChange={handleEditValueChange}
                onSaveEditItem={() => void saveEditItem()}
              />
            </TabsContent>

            <TabsContent value="stats">
              <StatsTab stats={stats} loading={loading} onRetry={fetchStats} />
            </TabsContent>
          </div>
        </TabsRoot>
      </div>
    </div>
  )
}
