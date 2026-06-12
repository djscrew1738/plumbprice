'use client'

import { useState, useCallback, useEffect, useRef, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import { RefreshCw, Wrench, DollarSign, BarChart3, Package, Briefcase, Users, TrendingUp, Eye, Flag, Upload, Activity, Database, Bell } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/Button'
import { type CanonicalItem, type CanonicalItemSupplier } from '@/lib/api'
import { useAdminTemplates, useAdminMarkups, useAdminItems, useAdminStats, useSaveMarkup, useSaveItem, type MarkupRule } from '@/lib/hooks'
import { useToast } from '@/components/ui/Toast'
import { PageShell, PageHeader } from '@/components/layout/shell'
import { ErrorState } from '@/components/ui/ErrorState'
import { TabsRoot, TabsList, TabsTrigger, TabsContent } from '@/components/ui/Tabs'
import { LaborTemplatesTab } from './LaborTemplatesTab'
import { MarkupRulesTab } from './MarkupRulesTab'
import { ItemPricesTab } from './ItemPricesTab'
import { StatsTab } from './StatsTab'
import { JobsPage } from './JobsPage'
import { AdminUsersPage } from './UsersPage'
import { AnalyticsTab } from './AnalyticsTab'
import { VisionMappingsTab } from './VisionMappingsTab'
import { FeatureFlagsTab } from './FeatureFlagsTab'
import { BulkImportPanel } from './BulkImportPanel'
import { CatalogBrowser } from './CatalogBrowser'
import { FeedStatusDashboard } from './FeedStatusDashboard'
import { PriceAlertsTab } from './PriceAlertsTab'

const SUPPLIERS = ['ferguson', 'moore_supply', 'apex'] as const
type SupplierSlug = typeof SUPPLIERS[number]

type EditValues = Record<SupplierSlug, Partial<CanonicalItemSupplier>>

const VALID_ADMIN_TABS = ['labor', 'markup', 'prices', 'stats', 'jobs', 'users', 'analytics', 'vision', 'flags', 'import', 'catalog', 'feeds', 'alerts'] as const

function AdminPageInner() {
  const searchParams = useSearchParams()
  const initialTab = searchParams.get('tab') ?? 'labor'
  const toast = useToast()
  const queryClient = useQueryClient()
  const [tab, setTab] = useState(VALID_ADMIN_TABS.includes(initialTab as typeof VALID_ADMIN_TABS[number]) ? initialTab : 'labor')
  const [markupRules, setMarkupRules] = useState<MarkupRule[]>([])
  const [saveOk, setSaveOk] = useState(false)
  const [confirmSave, setConfirmSave] = useState(false)
  const [priceSearch, setPriceSearch] = useState('')
  const [editItem, setEditItem] = useState<CanonicalItem | null>(null)
  const [editValues, setEditValues] = useState<EditValues>({} as EditValues)
  const [addItemOpen, setAddItemOpen] = useState(false)
  const [addItemName, setAddItemName] = useState('')
  const [addItemValues, setAddItemValues] = useState<EditValues>({} as EditValues)

  const { data: templates = [], isLoading: templatesLoading, error: templatesError } = useAdminTemplates({
    enabled: tab === 'labor',
  })

  const { data: markupData, isLoading: markupLoading, error: markupError, dataUpdatedAt: markupUpdatedAt } = useAdminMarkups({
    enabled: tab === 'markup',
  })

  // Track last-synced timestamp so we only sync new fetches
  const markupSyncedAtRef = useRef(0)
  useEffect(() => {
    if (markupData && markupUpdatedAt > markupSyncedAtRef.current) {
      setMarkupRules(markupData)
      markupSyncedAtRef.current = markupUpdatedAt
    }
  }, [markupData, markupUpdatedAt])

  const { data: canonicalItems = [], isLoading: pricesLoading, error: pricesError } = useAdminItems({
    enabled: tab === 'prices',
  })

  const { data: stats = null, isLoading: statsLoading, error: statsError } = useAdminStats({
    enabled: tab === 'stats',
  })

  const saveMarkupMutation = useSaveMarkup()
  const saveItemMutation = useSaveItem()
  const addItemMutation = useSaveItem()

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

  const openAddItem = useCallback(() => {
    const blank = {} as EditValues
    for (const slug of SUPPLIERS) {
      blank[slug] = { name: '', cost: 0, unit: 'ea', sku: '' }
    }
    setAddItemValues(blank)
    setAddItemName('')
    setAddItemOpen(true)
  }, [])

  const saveAddItem = useCallback(async () => {
    const name = addItemName.trim()
    if (!name) return
    const updates = SUPPLIERS
      .filter(slug => addItemValues[slug]?.name && (addItemValues[slug]?.cost ?? 0) > 0)
      .map(slug => ({
        supplier: slug,
        name: addItemValues[slug].name!,
        cost: Number(addItemValues[slug].cost),
        unit: addItemValues[slug].unit ?? 'ea',
        sku: addItemValues[slug].sku || undefined,
      }))
    if (updates.length === 0) return
    addItemMutation.mutate(
      { canonicalItem: name, updates },
      {
        onSuccess: () => {
          toast.success('Item added', name)
          setAddItemOpen(false)
          void queryClient.invalidateQueries({ queryKey: ['admin', 'items'] })
        },
        onError: () => toast.error('Could not add item', 'Please try again.'),
      },
    )
  }, [addItemName, addItemValues, addItemMutation, toast, queryClient])

  const handleAddItemValueChange = useCallback((slug: SupplierSlug, field: string, value: string | number) => {
    setAddItemValues(prev => ({ ...prev, [slug]: { ...prev[slug], [field]: value } }))
  }, [])

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
    if (tab === 'jobs') { void queryClient.invalidateQueries({ queryKey: ['admin', 'tasks'] }); return }
    if (tab === 'users') { void queryClient.invalidateQueries({ queryKey: ['admin'] }); return }
    if (tab === 'analytics') { void queryClient.invalidateQueries({ queryKey: ['analytics'] }); return }
    void queryClient.invalidateQueries({ queryKey: ['admin', 'stats'] })
  }

  const handleEditValueChange = useCallback((slug: SupplierSlug, field: string, value: string | number) => {
    setEditValues(prev => ({ ...prev, [slug]: { ...prev[slug], [field]: value } }))
  }, [])

  const handleTabChange = useCallback((value: string) => {
    setTab(value)
    // Update URL query param so the tab is bookmarkable
    const url = new URL(window.location.href)
    url.searchParams.set('tab', value)
    window.history.replaceState({}, '', url)
  }, [])

  return (
    <PageShell width="narrow">
      <PageHeader
        eyebrow="Admin Controls"
        title="Tune pricing rules and template baselines."
        description="Manage labor templates, markup settings, and estimator health stats from one control surface."
        actions={(
          <Button
              variant="secondary"
              size="sm"
              onClick={refreshCurrentTab}
              isLoading={loading}
              aria-label="Refresh"
            >
              <RefreshCw size={14} />
              <span className="hidden sm:inline">Refresh</span>
            </Button>
          )}
        />

        <TabsRoot value={tab} onChange={handleTabChange} className="mt-4">
          <TabsList>
            <TabsTrigger value="labor" icon={Wrench}>Labor Templates</TabsTrigger>
            <TabsTrigger value="markup" icon={DollarSign}>Markup Rules</TabsTrigger>
            <TabsTrigger value="prices" icon={Package}>Item Prices</TabsTrigger>
            <TabsTrigger value="stats" icon={BarChart3}>Stats</TabsTrigger>
            <TabsTrigger value="jobs" icon={Briefcase}>Jobs</TabsTrigger>
            <TabsTrigger value="users" icon={Users}>Users</TabsTrigger>
            <TabsTrigger value="analytics" icon={TrendingUp}>Analytics</TabsTrigger>
            <TabsTrigger value="vision" icon={Eye}>Vision Map</TabsTrigger>
            <TabsTrigger value="flags" icon={Flag}>Feature Flags</TabsTrigger>
            <TabsTrigger value="import" icon={Upload}>Bulk Import</TabsTrigger>
            <TabsTrigger value="catalog" icon={Database}>Catalog</TabsTrigger>
            <TabsTrigger value="feeds" icon={Activity}>Feeds</TabsTrigger>
            <TabsTrigger value="alerts" icon={Bell}>Price Alerts</TabsTrigger>
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
                addItemOpen={addItemOpen}
                addItemName={addItemName}
                addItemValues={addItemValues}
                addItemSaving={addItemMutation.isPending}
                onOpenAddItem={openAddItem}
                onCloseAddItem={() => setAddItemOpen(false)}
                onAddItemNameChange={setAddItemName}
                onAddItemValueChange={handleAddItemValueChange}
                onSaveAddItem={() => void saveAddItem()}
              />
            </TabsContent>

            <TabsContent value="stats">
              <StatsTab stats={stats} loading={loading} onRetry={() => void queryClient.invalidateQueries({ queryKey: ['admin', 'stats'] })} />
            </TabsContent>

            <TabsContent value="jobs">
              <JobsPage />
            </TabsContent>

            <TabsContent value="users">
              <AdminUsersPage />
            </TabsContent>

            <TabsContent value="analytics">
              <AnalyticsTab />
            </TabsContent>

            <TabsContent value="vision">
              <VisionMappingsTab />
            </TabsContent>

            <TabsContent value="flags">
              <FeatureFlagsTab />
            </TabsContent>

            <TabsContent value="import">
              <BulkImportPanel />
            </TabsContent>

            <TabsContent value="catalog">
              <CatalogBrowser />
            </TabsContent>

            <TabsContent value="feeds">
              <FeedStatusDashboard />
            </TabsContent>

            <TabsContent value="alerts">
              <PriceAlertsTab />
            </TabsContent>
          </div>
        </TabsRoot>
    </PageShell>
  )
}

export function AdminPage() {
  return (
    <Suspense fallback={<div className="min-h-[60dvh] p-4">Loading admin…</div>}>
      <AdminPageInner />
    </Suspense>
  )
}
