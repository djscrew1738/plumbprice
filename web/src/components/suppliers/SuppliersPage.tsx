'use client'

import { useState, useMemo, useCallback } from 'react'
import { AnimatePresence } from 'framer-motion'
import { RefreshCw } from 'lucide-react'
import { useSuppliers, usePriceCacheStats, useRefreshPrices } from '@/lib/hooks'
import { PageShell, PageHeader } from '@/components/layout/shell'
import { useToast } from '@/components/ui/Toast'
import { Skeleton } from '@/components/ui/Skeleton'
import { EmptyState } from '@/components/ui/EmptyState'
import { ErrorState } from '@/components/ui/ErrorState'
import { Alert } from '@/components/ui/Alert'
import { COPY_FEEDBACK_MS } from '@/lib/constants'
import { formatRelativeTimeShort } from '@/lib/formatters'
import dynamic from 'next/dynamic'
import { SupplierPriceCacheDashboard } from './SupplierPriceCacheDashboard'
import { SupplierCatalogStats } from './SupplierCatalogStats'
import { SupplierSearchAndFilters } from './SupplierSearchAndFilters'
import { SupplierItemCard } from './SupplierItemCard'
import { SupplierComparisonTable } from './SupplierComparisonTable'

const ConfirmDialog = dynamic(() => import('@/components/ui/ConfirmDialog').then(m => ({ default: m.ConfirmDialog })), { ssr: false })
const PriceHistoryModal = dynamic(() => import('./PriceHistoryModal').then(m => ({ default: m.PriceHistoryModal })), { ssr: false })

export const SUPPLIER_LABELS: Record<string, string> = {
  ferguson: 'Ferguson',
  moore_supply: 'Moore Supply',
  apex: 'Apex',
}

const SUPPLIERS = ['ferguson', 'moore_supply', 'apex']

export function SuppliersPage() {
  const toast = useToast()
  const [expanded,       setExpanded]       = useState<string | null>(null)
  const [search,         setSearch]         = useState('')
  const [activeCategory, setActiveCategory] = useState('all')
  const [copiedSku,      setCopiedSku]      = useState<string | null>(null)
  const [showConfirm,    setShowConfirm]    = useState(false)
  const [staleDismissed, setStaleDismissed] = useState(false)
  const [historyModal,   setHistoryModal]   = useState<{ itemId: string; itemName: string } | null>(null)
  const [activeTab,      setActiveTab]      = useState<'catalog' | 'cache'>('catalog')

  const copySku = (sku: string) => {
    void navigator.clipboard.writeText(sku).then(() => {
      setCopiedSku(sku)
      toast.success('SKU copied', sku)
      setTimeout(() => setCopiedSku(null), COPY_FEEDBACK_MS)
    })
  }

  const { data: items = [], isLoading: loading, error: queryError, refetch: fetchCatalog } = useSuppliers()
  const { data: cacheStats, isLoading: cacheLoading } = usePriceCacheStats()
  const refreshMutation = useRefreshPrices()

  const error = queryError ? 'Could not load supplier catalog' : null

  const handleRefreshAll = useCallback(() => {
    refreshMutation.mutate(undefined, {
      onSuccess: () => {
        toast.success('Price refresh started', 'All supplier prices are being updated')
        setShowConfirm(false)
      },
      onError: () => toast.error('Refresh failed', 'Could not trigger price refresh'),
    })
  }, [refreshMutation, toast])

  const handleRefreshSupplier = useCallback((supplierId: string) => {
    refreshMutation.mutate(supplierId, {
      onSuccess: () => toast.success('Refresh started', `${SUPPLIER_LABELS[supplierId] ?? supplierId} prices updating`),
      onError: () => toast.error('Refresh failed', 'Could not trigger price refresh'),
    })
  }, [refreshMutation, toast])

  const categories = useMemo(() => {
    return [...new Set(items.map(i => i.category))].sort()
  }, [items])

  const filtered = useMemo(() => {
    return items.filter(item => {
      const matchCat = activeCategory === 'all' || item.category === activeCategory
      const q = search.toLowerCase()
      const matchSearch = !q || item.display_name.toLowerCase().includes(q) || item.canonical_id.toLowerCase().includes(q)
      return matchCat && matchSearch
    })
  }, [items, search, activeCategory])

  const avgBest = useMemo(() =>
    filtered.length > 0
      ? filtered.reduce((s, i) => s + i.best_price, 0) / filtered.length
      : 0,
    [filtered]
  )

  const hasStaleWarning = !staleDismissed && cacheStats && (cacheStats.stale_count ?? 0) > 0

  const openHistory = useCallback((item: { canonical_id: string; display_name: string }) => {
    setHistoryModal({ itemId: item.canonical_id, itemName: item.display_name })
  }, [])

  return (
    <PageShell width="default">

      {/* Stale prices alert */}
      {hasStaleWarning && (
        <div className="mb-4">
          <Alert
            variant="warning"
            title={`${cacheStats.stale_count} stale price${cacheStats.stale_count === 1 ? '' : 's'} detected`}
            description="Some cached prices may be outdated. Refresh to get the latest supplier pricing."
            dismissible
            onDismiss={() => setStaleDismissed(true)}
            action={
              <button
                onClick={() => setShowConfirm(true)}
                disabled={refreshMutation.isPending}
                className="text-xs font-semibold underline underline-offset-2 hover:no-underline"
              >
                Refresh all prices
              </button>
            }
          />
        </div>
      )}

      <PageHeader
        eyebrow="Supplier Matrix"
        title="Compare catalog pricing side by side."
        description="Check the lowest supplier cost per item without leaving the workspace shell."
        actions={(
          <div className="flex items-center gap-2">
            <button
              onClick={() => void fetchCatalog()}
              disabled={loading}
              className="btn-secondary min-h-0 px-3 py-2"
              aria-label="Refresh supplier catalog"
            >
              <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
            </button>
          </div>
        )}
      />

      <div className="space-y-3">
        {/* Tab toggle */}
        <div className="flex items-center gap-1 border-b border-[color:var(--line)] pb-0">
          <TabButton active={activeTab === 'catalog'} onClick={() => setActiveTab('catalog')}>
            Catalog
          </TabButton>
          <TabButton active={activeTab === 'cache'} onClick={() => setActiveTab('cache')}>
            <span className="flex items-center gap-1.5">
              Price Cache
              {cacheStats && (cacheStats.stale_count ?? 0) > 0 && (
                <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
              )}
            </span>
          </TabButton>
        </div>

        {/* Cache dashboard tab */}
        {activeTab === 'cache' && (
          <SupplierPriceCacheDashboard
            cachedItems={cacheStats?.cached_items as number | undefined}
            hitRate={cacheStats?.hit_rate as number | undefined}
            staleCount={cacheStats?.stale_count as number | undefined}
            lastRefresh={formatRelativeTimeShort(cacheStats?.last_refresh as string | undefined)}
            loading={cacheLoading}
            refreshing={refreshMutation.isPending}
            suppliers={SUPPLIERS}
            supplierLabels={SUPPLIER_LABELS}
            itemCount={items.length}
            onRefreshAll={() => setShowConfirm(true)}
            onRefreshSupplier={handleRefreshSupplier}
          />
        )}

        {/* Catalog tab */}
        {activeTab === 'catalog' && (
          <>
            <SupplierCatalogStats filteredCount={filtered.length} totalCount={items.length} avgBest={avgBest} />

            <SupplierSearchAndFilters
              search={search}
              onSearchChange={setSearch}
              categories={categories}
              activeCategory={activeCategory}
              onCategoryChange={setActiveCategory}
            />
          </>
        )}
      </div>

      <div className="mt-4">
        {activeTab === 'catalog' && loading && (
          <div className="space-y-2">
            {Array.from({ length: 8 }).map((_, i) => (
              <Skeleton key={i} variant="card" className="h-16 rounded-xl" />
            ))}
          </div>
        )}

        {activeTab === 'catalog' && error && !loading && (
          <ErrorState
            message={error}
            onRetry={() => void fetchCatalog()}
            className="card"
          />
        )}

        {activeTab === 'catalog' && !loading && !error && filtered.length === 0 && (
          <EmptyState
            icon={<svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m7.5 4.27 9 5.15"/><path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/></svg>}
            title={search || activeCategory !== 'all' ? 'No items match your filter' : 'No catalog data available'}
            description={search || activeCategory !== 'all' ? 'Try adjusting your search or filters' : 'Check back soon'}
            action={(search || activeCategory !== 'all') ? (
              <button onClick={() => { setSearch(''); setActiveCategory('all') }} className="btn-ghost text-xs">
                Clear filters
              </button>
            ) : undefined}
            className="card"
          />
        )}

        {activeTab === 'catalog' && !loading && !error && filtered.length > 0 && (
          <>
            {/* Mobile: expandable cards */}
            <div className="space-y-2 lg:hidden">
              <AnimatePresence initial={false}>
                {filtered.map(item => (
                  <SupplierItemCard
                    key={item.canonical_id}
                    item={item}
                    isOpen={expanded === item.canonical_id}
                    onToggle={() => setExpanded(expanded === item.canonical_id ? null : item.canonical_id)}
                    onHistory={openHistory}
                    onCopySku={copySku}
                    copiedSku={copiedSku}
                    suppliers={SUPPLIERS}
                    supplierLabels={SUPPLIER_LABELS}
                  />
                ))}
              </AnimatePresence>
            </div>

            {/* Desktop table */}
            <div className="hidden lg:block">
              <SupplierComparisonTable
                items={filtered}
                suppliers={SUPPLIERS}
                supplierLabels={SUPPLIER_LABELS}
                onHistory={openHistory}
              />
            </div>
          </>
        )}
      </div>

      {/* Confirm dialog for refresh all */}
      <ConfirmDialog
        open={showConfirm}
        onClose={() => setShowConfirm(false)}
        onConfirm={handleRefreshAll}
        title="Refresh All Prices"
        description="This will re-fetch pricing from all suppliers. The process may take a minute. Continue?"
        confirmLabel="Refresh"
        isLoading={refreshMutation.isPending}
      />

      {/* Price history modal */}
      {historyModal && (
        <PriceHistoryModal
          open={!!historyModal}
          onClose={() => setHistoryModal(null)}
          itemId={historyModal.itemId}
          itemName={historyModal.itemName}
        />
      )}
    </PageShell>
  )
}

function TabButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={`
        -mb-px border-b-2 px-3 py-1.5 text-xs font-semibold transition-colors
        ${active
          ? 'border-[color:var(--accent)] text-[color:var(--accent)]'
          : 'border-transparent text-[color:var(--muted-ink)] hover:text-[color:var(--ink)]'}
      `}
    >
      {children}
    </button>
  )
}
