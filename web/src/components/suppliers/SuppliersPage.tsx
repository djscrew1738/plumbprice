'use client'

import { useState, useMemo } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { RefreshCw, TrendingDown, Package, DollarSign, ChevronDown, ChevronUp, Search, X, Copy, Check } from 'lucide-react'
import { cn, formatCurrencyDecimal } from '@/lib/utils'
import { api } from '@/lib/api'
import { PageIntro } from '@/components/layout/PageIntro'
import { useToast } from '@/components/ui/Toast'
import { Badge } from '@/components/ui/Badge'
import { Skeleton } from '@/components/ui/Skeleton'
import { EmptyState } from '@/components/ui/EmptyState'
import { ErrorState } from '@/components/ui/ErrorState'
import { Tooltip } from '@/components/ui/Tooltip'

interface SupplierPrice { name: string; sku: string; cost: number }
interface CatalogItem {
  canonical_id: string
  display_name: string
  category: string
  best_price: number
  best_supplier: string
  prices: { ferguson?: SupplierPrice; moore_supply?: SupplierPrice; apex?: SupplierPrice }
}

const SUPPLIER_LABELS: Record<string, string> = {
  ferguson: 'Ferguson',
  moore_supply: 'Moore Supply',
  apex: 'Apex',
}

function prettyCat(cat: string) {
  return cat.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

export function SuppliersPage() {
  const toast = useToast()
  const queryClient = useQueryClient()
  const [expanded,       setExpanded]       = useState<string | null>(null)
  const [search,         setSearch]         = useState('')
  const [activeCategory, setActiveCategory] = useState('all')
  const [copiedSku,      setCopiedSku]      = useState<string | null>(null)

  const copySku = (sku: string) => {
    void navigator.clipboard.writeText(sku).then(() => {
      setCopiedSku(sku)
      toast.success('SKU copied', sku)
      setTimeout(() => setCopiedSku(null), 2000)
    })
  }

  const { data: items = [], isLoading: loading, error: queryError, refetch: fetchCatalog } = useQuery({
    queryKey: ['suppliers'],
    queryFn: async () => {
      const res = await api.get('/suppliers/catalog')
      const raw: Record<string, Record<string, { sku: string; name: string; cost: number }>> =
        res.data?.items ?? res.data ?? {}
      return Object.entries(raw).map(([canonical_id, prices]): CatalogItem => {
        const entries = Object.entries(prices) as [string, { sku: string; name: string; cost: number }][]
        let best_supplier = entries[0]?.[0] ?? ''
        let best_price    = entries[0]?.[1]?.cost ?? 0
        for (const [sup, p] of entries) {
          if (p.cost < best_price) { best_price = p.cost; best_supplier = sup }
        }
        return {
          canonical_id,
          display_name: canonical_id.replace(/\./g, ' › ').replace(/_/g, ' '),
          category: canonical_id.split('.')[0] ?? 'other',
          best_price,
          best_supplier,
          prices: prices as CatalogItem['prices'],
        }
      })
    },
  })

  const error = queryError ? 'Could not load supplier catalog' : null

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

  const avgBest = filtered.length > 0
    ? filtered.reduce((s, i) => s + i.best_price, 0) / filtered.length
    : 0

  const suppliers = ['ferguson', 'moore_supply', 'apex']

  return (
    <div className="min-h-full">
      <div className="mx-auto w-full max-w-5xl px-4 py-5 sm:px-6 lg:px-8">
        <PageIntro
          eyebrow="Supplier Matrix"
          title="Compare catalog pricing side by side."
          description="Check the lowest supplier cost per item without leaving the workspace shell."
          actions={(
            <button
              onClick={() => void fetchCatalog()}
              disabled={loading}
              className="btn-secondary min-h-0 px-3 py-2"
              aria-label="Refresh supplier catalog"
            >
              <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
            </button>
          )}
        >
          <div className="space-y-3">
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
          </div>
        </PageIntro>

        <div className="mt-4">

        {loading && (
          <div className="space-y-2">
            {Array.from({ length: 8 }).map((_, i) => (
              <Skeleton key={i} variant="card" className="h-16 rounded-xl" />
            ))}
          </div>
        )}

        {error && !loading && (
          <ErrorState
            message={error}
            onRetry={() => void fetchCatalog()}
            className="card"
          />
        )}

        {!loading && !error && filtered.length === 0 && (
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

        {!loading && !error && filtered.length > 0 && (
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
                        {isOpen ? <ChevronUp size={15} className="text-[color:var(--muted-ink)] shrink-0" /> : <ChevronDown size={15} className="text-[color:var(--muted-ink)] shrink-0" />}
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
                                    <div className={cn('text-sm font-bold tabular-nums', isBest ? 'text-emerald-700' : 'text-[color:var(--muted-ink)]')}>
                                      {formatCurrencyDecimal(p.cost)}
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
                          return (
                            <td key={sup} className={cn('px-4 py-3 text-right tabular-nums', isBest ? 'text-[hsl(var(--success))] font-semibold' : 'text-[color:var(--muted-ink)]')}>
                              {p ? formatCurrencyDecimal(p.cost) : <span className="text-[color:var(--muted-ink)]">—</span>}
                            </td>
                          )
                        })}
                        <td className="px-4 py-3 text-right">
                          <Badge variant="success" size="sm" dot>
                            <TrendingDown size={10} />
                            {formatCurrencyDecimal(item.best_price)}
                          </Badge>
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
    </div>
  )
}
