'use client'

import { useState, useMemo, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  RefreshCw, TrendingDown, TrendingUp, Package, DollarSign,
  ChevronDown, ChevronUp, Search, X, Copy, Check, Database, Zap, AlertTriangle, Clock, History,
} from 'lucide-react'
import { cn, formatCurrencyDecimal } from '@/lib/utils'
import { useSuppliers, usePriceCacheStats, useRefreshPrices } from '@/lib/hooks'
import { PageIntro } from '@/components/layout/PageIntro'
import { useToast } from '@/components/ui/Toast'
import { Badge } from '@/components/ui/Badge'
import { Skeleton } from '@/components/ui/Skeleton'
import { EmptyState } from '@/components/ui/EmptyState'
import { ErrorState } from '@/components/ui/ErrorState'
import { Tooltip } from '@/components/ui/Tooltip'
import { StatCard } from '@/components/ui/StatCard'
import { Alert } from '@/components/ui/Alert'
import dynamic from 'next/dynamic'

const ConfirmDialog = dynamic(() => import('@/components/ui/ConfirmDialog').then(m => ({ default: m.ConfirmDialog })), { ssr: false })
const PriceHistoryModal = dynamic(() => import('./PriceHistoryModal').then(m => ({ default: m.PriceHistoryModal })), { ssr: false })

const SUPPLIER_LABELS: Record<string, string> = {
  ferguson: 'Ferguson',
  moore_supply: 'Moore Supply',
  apex: 'Apex',
}

function prettyCat(cat: string) {
  return cat.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

function relativeTime(dateStr: string | null | undefined): string {
  if (!dateStr) return 'Never'
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60_000)
  if (mins < 1) return 'Just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

// ─── Price change indicator ─────────────────────────────────────────────────

function PriceChangeIndicator({ changePct }: { changePct: number | undefined | null }) {
  if (changePct == null || changePct === 0) return null
  const isIncrease = changePct > 0
  return (
    <Tooltip
      content={isIncrease ? 'Price increased recently' : 'Price decreased recently'}
      side="top"
    >
      <span className={cn(
        'inline-flex items-center gap-0.5 text-[10px] font-bold tabular-nums rounded-full px-1.5 py-0.5',
        isIncrease
          ? 'bg-red-500/10 text-red-600'
          : 'bg-emerald-500/10 text-emerald-600',
      )}>
        {isIncrease ? <TrendingUp size={10} /> : <TrendingDown size={10} />}
        {isIncrease ? '+' : ''}{changePct.toFixed(1)}%
      </span>
    </Tooltip>
  )
}

// ─── Main component ─────────────────────────────────────────────────────────

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
      setTimeout(() => setCopiedSku(null), 2000)
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
    const cats = [...new Set(items.map(i => i.category))].sort()
    return cats
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

  const suppliers = ['ferguson', 'moore_supply', 'apex']

  const hasStaleWarning = !staleDismissed && cacheStats && cacheStats.stale_count > 0

  return (
    <div className="min-h-full">
      <div className="mx-auto w-full max-w-5xl px-4 py-5 sm:px-6 lg:px-8">

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

        <PageIntro
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
        >
          <div className="space-y-3">
            {/* Tab toggle */}
            <div className="flex items-center gap-1 border-b border-[color:var(--line)] pb-0">
              <button
                onClick={() => setActiveTab('catalog')}
                className={cn(
                  'px-3 py-1.5 text-xs font-semibold border-b-2 transition-colors -mb-px',
                  activeTab === 'catalog'
                    ? 'border-[color:var(--accent)] text-[color:var(--accent)]'
                    : 'border-transparent text-[color:var(--muted-ink)] hover:text-[color:var(--ink)]',
                )}
              >
                Catalog
              </button>
              <button
                onClick={() => setActiveTab('cache')}
                className={cn(
                  'px-3 py-1.5 text-xs font-semibold border-b-2 transition-colors -mb-px flex items-center gap-1.5',
                  activeTab === 'cache'
                    ? 'border-[color:var(--accent)] text-[color:var(--accent)]'
                    : 'border-transparent text-[color:var(--muted-ink)] hover:text-[color:var(--ink)]',
                )}
              >
                Price Cache
                {cacheStats && cacheStats.stale_count > 0 && (
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                )}
              </button>
            </div>

            {/* Cache dashboard tab */}
            {activeTab === 'cache' && (
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
                  <StatCard
                    icon={Database}
                    label="Cached Items"
                    value={cacheStats?.cached_items ?? '—'}
                    loading={cacheLoading}
                    variant="default"
                  />
                  <StatCard
                    icon={Zap}
                    label="Hit Rate"
                    value={cacheStats ? `${(cacheStats.hit_rate * 100).toFixed(1)}%` : '—'}
                    loading={cacheLoading}
                    variant="success"
                  />
                  <StatCard
                    icon={AlertTriangle}
                    label="Stale Items"
                    value={cacheStats?.stale_count ?? '—'}
                    loading={cacheLoading}
                    variant={cacheStats && cacheStats.stale_count > 0 ? 'warning' : 'default'}
                  />
                  <StatCard
                    icon={Clock}
                    label="Last Refresh"
                    value={relativeTime(cacheStats?.last_refresh)}
                    loading={cacheLoading}
                    variant="default"
                  />
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <button
                    onClick={() => setShowConfirm(true)}
                    disabled={refreshMutation.isPending}
                    className={cn(
                      'btn-secondary min-h-0 px-3 py-2 text-xs font-semibold flex items-center gap-1.5',
                    )}
                    aria-label="Refresh all supplier prices"
                  >
                    <RefreshCw size={13} className={refreshMutation.isPending ? 'animate-spin' : ''} />
                    Refresh All Prices
                  </button>

                  {suppliers.map(sup => (
                    <button
                      key={sup}
                      onClick={() => handleRefreshSupplier(sup)}
                      disabled={refreshMutation.isPending}
                      className="btn-secondary min-h-0 px-2.5 py-1.5 text-[11px] font-semibold flex items-center gap-1"
                      aria-label={`Refresh ${SUPPLIER_LABELS[sup] ?? sup} prices`}
                    >
                      <RefreshCw size={11} className={refreshMutation.isPending ? 'animate-spin' : ''} />
                      {SUPPLIER_LABELS[sup]}
                    </button>
                  ))}
                </div>

                {refreshMutation.isPending && (
                  <div className="flex items-center gap-2 text-xs text-[color:var(--muted-ink)]" role="status" aria-live="polite">
                    <RefreshCw size={12} className="animate-spin text-emerald-500 shrink-0" />
                    <span>Refreshing prices for {items.length > 0 ? `${items.length} items` : 'all items'}…</span>
                    <div className="flex-1 h-1 bg-emerald-100 rounded-full overflow-hidden min-w-[60px]">
                      <div className="h-full w-2/5 bg-emerald-400 rounded-full animate-pulse" />
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Catalog tab */}
            {activeTab === 'catalog' && (
              <>
                <div className="grid grid-cols-1 gap-2.5 md:grid-cols-3">
                  <div className="card-inset flex items-center gap-2.5 p-3">
                    <div className="w-8 h-8 bg-blue-500/10 border border-blue-500/20 rounded-xl flex items-center justify-center">
                      <Package size={14} className="text-blue-700" />
                    </div>
                    <div>
                      <div className="text-[10px] text-[color:var(--muted-ink)] leading-none font-medium uppercase tracking-wider">Showing</div>
                      <div className="text-sm font-bold text-[color:var(--ink)]">{filtered.length} <span className="text-[color:var(--muted-ink)] font-normal text-xs">of {items.length}</span></div>
                    </div>
                  </div>
                  <div className="card-inset flex items-center gap-2.5 p-3">
                    <div className="w-8 h-8 bg-emerald-500/10 border border-emerald-500/20 rounded-xl flex items-center justify-center">
                      <DollarSign size={14} className="text-emerald-700" />
                    </div>
                    <div>
                      <div className="text-[10px] text-[color:var(--muted-ink)] leading-none font-medium uppercase tracking-wider">Avg Best</div>
                      <div className="text-sm font-bold text-[color:var(--ink)]">{formatCurrencyDecimal(avgBest)}</div>
                    </div>
                  </div>
                  <div className="card-inset flex items-center gap-2.5 p-3">
                    <div className="w-8 h-8 bg-violet-500/10 border border-violet-500/20 rounded-xl flex items-center justify-center">
                      <TrendingDown size={14} className="text-violet-700" />
                    </div>
                    <div>
                      <div className="text-[10px] text-[color:var(--muted-ink)] leading-none font-medium uppercase tracking-wider">Suppliers</div>
                      <div className="text-sm font-bold text-[color:var(--ink)]">Ferguson · Moore · Apex</div>
                    </div>
                  </div>
                </div>

                <div className="relative">
                  <Search size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[color:var(--muted-ink)] pointer-events-none" />
                  <input
                    value={search}
                    onChange={e => setSearch(e.target.value)}
                    placeholder="Search items…"
                    className="input py-2.5 pl-9 pr-9"
                  />
                  {search && (
                    <button onClick={() => setSearch('')} className="absolute right-3 top-1/2 -translate-y-1/2 text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] transition-colors" aria-label="Clear search">
                      <X size={14} />
                    </button>
                  )}
                </div>

                {categories.length > 0 && (
                  <div className="flex items-center gap-1.5 overflow-x-auto scrollbar-hide pb-0.5">
                    <button
                      onClick={() => setActiveCategory('all')}
                      aria-label="Show all categories"
                      aria-pressed={activeCategory === 'all'}
                      className={cn(
                        'shrink-0 px-2.5 py-1 rounded-full text-[11px] font-semibold transition-all border',
                        activeCategory === 'all'
                          ? 'border-[color:var(--accent)] bg-[color:var(--accent)] text-white'
                          : 'border-[color:var(--line)] bg-[color:var(--panel)] text-[color:var(--muted-ink)] hover:bg-[color:var(--panel-strong)] hover:text-[color:var(--ink)]',
                      )}
                    >
                      All
                    </button>
                    {categories.map(cat => (
                      <button
                        key={cat}
                        onClick={() => setActiveCategory(cat)}
                        aria-label={`Filter by ${prettyCat(cat)}`}
                        aria-pressed={activeCategory === cat}
                        className={cn(
                          'shrink-0 px-2.5 py-1 rounded-full text-[11px] font-semibold whitespace-nowrap transition-all border',
                          activeCategory === cat
                            ? 'border-[color:var(--accent)] bg-[color:var(--accent)] text-white'
                            : 'border-[color:var(--line)] bg-[color:var(--panel)] text-[color:var(--muted-ink)] hover:bg-[color:var(--panel-strong)] hover:text-[color:var(--ink)]',
                        )}
                      >
                        {prettyCat(cat)}
                      </button>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        </PageIntro>

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
            icon={<Package size={28} />}
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
                {filtered.map(item => {
                  const isOpen = expanded === item.canonical_id
                  return (
                    <motion.div
                      key={item.canonical_id}
                      layout
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="card overflow-hidden transition-all hover:-translate-y-0.5 hover:shadow-lg"
                    >
                      <button
                        className="w-full flex items-center justify-between px-4 py-3.5 text-left"
                        onClick={() => setExpanded(isOpen ? null : item.canonical_id)}
                      >
                        <div className="flex-1 min-w-0 mr-3">
                          <h3 className="text-sm font-semibold text-[color:var(--ink)] truncate">{item.display_name}</h3>
                          <div className="flex items-center gap-2 mt-0.5">
                            <Badge variant="success" size="sm" dot>
                              <TrendingDown size={10} />
                              {formatCurrencyDecimal(item.best_price)}
                            </Badge>
                            <span className="text-[11px] text-[color:var(--muted-ink)]">{SUPPLIER_LABELS[item.best_supplier] ?? item.best_supplier}</span>
                          </div>
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          <Tooltip content="View price history">
                            <button
                              onClick={e => { e.stopPropagation(); setHistoryModal({ itemId: item.canonical_id, itemName: item.display_name }) }}
                              className="flex min-h-[28px] min-w-[28px] items-center justify-center rounded-lg p-1.5 text-[color:var(--muted-ink)] hover:bg-[color:var(--panel-strong)] hover:text-[color:var(--ink)] transition-colors"
                              aria-label={`View price history for ${item.display_name}`}
                            >
                              <History size={13} />
                            </button>
                          </Tooltip>
                          {isOpen ? <ChevronUp size={15} className="text-[color:var(--muted-ink)]" /> : <ChevronDown size={15} className="text-[color:var(--muted-ink)]" />}
                        </div>
                      </button>

                      <AnimatePresence initial={false}>
                        {isOpen && (
                          <motion.div
                            initial={{ height: 0 }}
                            animate={{ height: 'auto' }}
                            exit={{ height: 0 }}
                            transition={{ type: 'spring', stiffness: 400, damping: 35 }}
                            className="overflow-hidden"
                          >
                            <div className="border-t border-[color:var(--line)] divide-y divide-[color:var(--line)]">
                              {suppliers.map(sup => {
                                const p = item.prices?.[sup as keyof typeof item.prices]
                                if (!p) return null
                                const isBest = sup === item.best_supplier
                                const changePct = (p as SupplierPriceExt).change_pct
                                return (
                                  <div key={sup} className={cn('flex items-center justify-between px-4 py-3', isBest && 'bg-emerald-500/[0.04]')}>
                                    <div>
                                      <div className={cn('text-xs font-semibold flex items-center gap-1.5', isBest ? 'text-emerald-700' : 'text-[color:var(--ink)]')}>
                                        {SUPPLIER_LABELS[sup]}
                                        {isBest && <Badge variant="success" size="sm">BEST</Badge>}
                                      </div>
                                      <div className="flex items-center gap-1.5 mt-0.5">
                                        <span className="text-[11px] text-[color:var(--muted-ink)] font-mono">{p.sku}</span>
                                        <Tooltip content="Copy SKU">
                                          <button
                                            onClick={e => { e.stopPropagation(); copySku(p.sku) }}
                                            className="flex min-h-[28px] min-w-[28px] items-center justify-center rounded-lg p-1.5 text-[color:var(--muted-ink)] hover:bg-[color:var(--panel-strong)] hover:text-[color:var(--ink)] transition-colors"
                                            aria-label={`Copy SKU ${p.sku}`}
                                          >
                                            {copiedSku === p.sku ? <Check size={12} className="text-emerald-600" /> : <Copy size={12} />}
                                          </button>
                                        </Tooltip>
                                      </div>
                                    </div>
                                    <div className="flex items-center gap-2">
                                      <PriceChangeIndicator changePct={changePct} />
                                      <div className={cn('text-sm font-bold tabular-nums', isBest ? 'text-emerald-700' : 'text-[color:var(--muted-ink)]')}>
                                        {formatCurrencyDecimal(p.cost)}
                                      </div>
                                    </div>
                                  </div>
                                )
                              })}
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </motion.div>
                  )
                })}
              </AnimatePresence>
            </div>

            {/* Desktop table */}
            <div className="hidden lg:block card overflow-hidden">
              <table className="w-full text-sm">
                <thead className="sticky top-0">
                  <tr className="border-b border-[color:var(--line)] bg-[color:var(--panel-strong)]">
                    <th className="px-4 py-3 text-left text-[10px] font-bold text-[color:var(--muted-ink)] uppercase tracking-widest">Item</th>
                    <th className="px-4 py-3 text-right text-[10px] font-bold text-[color:var(--muted-ink)] uppercase tracking-widest">Ferguson</th>
                    <th className="px-4 py-3 text-right text-[10px] font-bold text-[color:var(--muted-ink)] uppercase tracking-widest">Moore Supply</th>
                    <th className="px-4 py-3 text-right text-[10px] font-bold text-[color:var(--muted-ink)] uppercase tracking-widest">Apex</th>
                    <th className="px-4 py-3 text-right text-[10px] font-bold text-[hsl(var(--success))] uppercase tracking-widest">Best Price</th>
                    <th className="w-10" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-[color:var(--line)]">
                  <AnimatePresence initial={false}>
                    {filtered.map(item => (
                      <motion.tr
                        key={item.canonical_id}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="hover:bg-[color:var(--panel-strong)] transition-all hover:-translate-y-0.5"
                      >
                        <td className="px-4 py-3 font-medium text-[color:var(--ink)]">{item.display_name}</td>
                        {suppliers.map(sup => {
                          const p = item.prices?.[sup as keyof typeof item.prices]
                          const isBest = sup === item.best_supplier
                          const changePct = (p as SupplierPriceExt | undefined)?.change_pct
                          return (
                            <td key={sup} className={cn('px-4 py-3 text-right', isBest ? 'text-[hsl(var(--success))] font-semibold' : 'text-[color:var(--muted-ink)]')}>
                              {p ? (
                                <span className="inline-flex items-center gap-1.5 tabular-nums">
                                  <PriceChangeIndicator changePct={changePct} />
                                  {formatCurrencyDecimal(p.cost)}
                                </span>
                              ) : (
                                <span className="text-[color:var(--muted-ink)]">—</span>
                              )}
                            </td>
                          )
                        })}
                        <td className="px-4 py-3 text-right">
                          <Badge variant="success" size="sm" dot>
                            <TrendingDown size={10} />
                            {formatCurrencyDecimal(item.best_price)}
                          </Badge>
                        </td>
                        <td className="px-2 py-3">
                          <Tooltip content="Price history">
                            <button
                              onClick={() => setHistoryModal({ itemId: item.canonical_id, itemName: item.display_name })}
                              className="flex min-h-[28px] min-w-[28px] items-center justify-center rounded-lg p-1.5 text-[color:var(--muted-ink)] hover:bg-[color:var(--panel-strong)] hover:text-[color:var(--ink)] transition-colors"
                              aria-label={`View price history for ${item.display_name}`}
                            >
                              <History size={13} />
                            </button>
                          </Tooltip>
                        </td>
                      </motion.tr>
                    ))}
                  </AnimatePresence>
                </tbody>
              </table>
            </div>
          </>
        )}
        </div>
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
    </div>
  )
}

// Extended type to accommodate optional change_pct from backend
interface SupplierPriceExt {
  name: string
  sku: string
  cost: number
  change_pct?: number
}
