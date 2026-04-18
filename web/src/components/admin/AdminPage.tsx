'use client'

import { useState, useCallback } from 'react'
import { RefreshCw, Wrench, DollarSign, BarChart3, Package } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import { type CanonicalItem, type CanonicalItemSupplier } from '@/lib/api'
import { useAdminTemplates, useAdminMarkups, useAdminItems, useAdminStats, useSaveMarkup, useSaveItem, type MarkupRule } from '@/lib/hooks'
import { useToast } from '@/components/ui/Toast'
import { PageIntro } from '@/components/layout/PageIntro'
import { ErrorState } from '@/components/ui/ErrorState'
import { TabsRoot, TabsList, TabsTrigger, TabsContent } from '@/components/ui/Tabs'
import { LaborTemplatesTab } from './LaborTemplatesTab'
import { MarkupRulesTab } from './MarkupRulesTab'
import { ItemPricesTab } from './ItemPricesTab'
import { StatsTab } from './StatsTab'

const SUPPLIERS = ['ferguson', 'moore_supply', 'apex'] as const
type SupplierSlug = typeof SUPPLIERS[number]

type EditValues = Record<SupplierSlug, Partial<CanonicalItemSupplier>>

export function AdminPage() {
  const toast = useToast()
  const queryClient = useQueryClient()
  const [tab, setTab] = useState('labor')
  const [markupRules, setMarkupRules] = useState<MarkupRule[]>([])
  const [saveOk, setSaveOk] = useState(false)
  const [confirmSave, setConfirmSave] = useState(false)
  const [priceSearch, setPriceSearch] = useState('')
  const [editItem, setEditItem] = useState<CanonicalItem | null>(null)
  const [editValues, setEditValues] = useState<EditValues>({} as EditValues)

  const { data: templates = [], isLoading: templatesLoading, error: templatesError } = useAdminTemplates({
    enabled: tab === 'labor',
  })

  const { data: markupData, isLoading: markupLoading, error: markupError, dataUpdatedAt: markupUpdatedAt } = useAdminMarkups({
    enabled: tab === 'markup',
  })

  // Track last-synced timestamp so we only sync new fetches
  const [markupSyncedAt, setMarkupSyncedAt] = useState(0)
  if (markupData && markupUpdatedAt > markupSyncedAt) {
    setMarkupRules(markupData)
    setMarkupSyncedAt(markupUpdatedAt)
  }

  const { data: canonicalItems = [], isLoading: pricesLoading, error: pricesError } = useAdminItems({
    enabled: tab === 'prices',
  })

  const { data: stats = null, isLoading: statsLoading, error: statsError } = useAdminStats({
    enabled: tab === 'stats',
  })

  const saveMarkupMutation = useSaveMarkup()
  const saveItemMutation = useSaveItem()

  const loading = (tab === 'labor' && templatesLoading) ||
    (tab === 'markup' && markupLoading) ||
    (tab === 'prices' && pricesLoading) ||
    (tab === 'stats' && statsLoading)

  const error = (tab === 'labor' && templatesError ? 'Failed to load templates' : null) ??
    (tab === 'markup' && markupError ? 'Failed to load markup rules' : null) ??
    (tab === 'prices' && pricesError ? 'Failed to load item prices' : null) ??
    (tab === 'stats' && statsError ? 'Failed to load stats' : null)

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
    const updates = SUPPLIERS
      .filter(slug => editValues[slug]?.name && (editValues[slug]?.cost ?? 0) > 0)
      .map(slug => ({
        supplier: slug,
        name: editValues[slug].name!,
        cost: Number(editValues[slug].cost),
        unit: editValues[slug].unit ?? 'ea',
        sku: editValues[slug].sku || undefined,
      }))
    saveItemMutation.mutate(
      { canonicalItem: editItem.canonical_item, updates },
      {
        onSuccess: () => {
          toast.success('Prices updated')
          setEditItem(null)
        },
        onError: () => toast.error('Could not save prices', 'Please try again.'),
      },
    )
  }, [editItem, editValues, toast, saveItemMutation])

  const saveMarkup = async () => {
    setConfirmSave(false)
    saveMarkupMutation.mutate(markupRules, {
      onSuccess: () => {
        toast.success('Markup rules saved')
        setSaveOk(true)
        setTimeout(() => setSaveOk(false), 3000)
      },
      onError: () => toast.error('Failed to save markup rules. Please try again.'),
    })
  }

  const updateMarkup = (jobType: string, field: keyof MarkupRule, rawValue: number) => {
    const value = field === 'materials_markup_pct'
      ? Math.min(200, Math.max(0, rawValue))
      : Math.min(500, Math.max(0, rawValue))
    setMarkupRules(prev => prev.map(r => r.job_type === jobType ? { ...r, [field]: value } : r))
  }

  const refreshCurrentTab = () => {
    if (tab === 'labor') { void queryClient.invalidateQueries({ queryKey: ['admin', 'templates'] }); return }
    if (tab === 'markup') { setMarkupRules([]); void queryClient.invalidateQueries({ queryKey: ['admin', 'markups'] }); return }
    if (tab === 'prices') { void queryClient.invalidateQueries({ queryKey: ['admin', 'items'] }); return }
    void queryClient.invalidateQueries({ queryKey: ['admin', 'stats'] })
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
                onRetry={refreshCurrentTab}
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
                saving={saveMarkupMutation.isPending}
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
                editSaving={saveItemMutation.isPending}
                onOpenEditItem={openEditItem}
                onCloseEditItem={() => setEditItem(null)}
                onEditValueChange={handleEditValueChange}
                onSaveEditItem={() => void saveEditItem()}
              />
            </TabsContent>

            <TabsContent value="stats">
              <StatsTab stats={stats} loading={loading} onRetry={() => void queryClient.invalidateQueries({ queryKey: ['admin', 'stats'] })} />
            </TabsContent>
          </div>
        </TabsRoot>
      </div>
    </div>
  )
}
