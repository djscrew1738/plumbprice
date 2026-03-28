'use client'

import { useState, useEffect, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { RefreshCw, TrendingDown, Package, DollarSign, ChevronDown, ChevronUp, Search, X } from 'lucide-react'
import { cn, formatCurrencyDecimal } from '@/lib/utils'
import axios from 'axios'

interface SupplierPrice { name: string; sku: string; cost: number }
interface CatalogItem {
  canonical_id: string
  display_name: string
  category: string
  best_price: number
  best_supplier: string
  prices: { ferguson?: SupplierPrice; moore_supply?: SupplierPrice; apex?: SupplierPrice }
}

const API = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000') + '/api/v1'
const SUPPLIER_LABELS: Record<string, string> = {
  ferguson: 'Ferguson',
  moore_supply: 'Moore Supply',
  apex: 'Apex',
}

function prettyCat(cat: string) {
  return cat.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

export function SuppliersPage() {
  const [items,       setItems]       = useState<CatalogItem[]>([])
  const [loading,     setLoading]     = useState(true)
  const [error,       setError]       = useState<string | null>(null)
  const [expanded,    setExpanded]    = useState<string | null>(null)
  const [search,      setSearch]      = useState('')
  const [activeCategory, setActiveCategory] = useState('all')

  const fetchCatalog = async () => {
    try {
      setLoading(true); setError(null)
      const res = await axios.get(`${API}/suppliers/catalog`)
      const raw: Record<string, Record<string, { sku: string; name: string; cost: number }>> =
        res.data?.items ?? res.data ?? {}
      const parsed: CatalogItem[] = Object.entries(raw).map(([canonical_id, prices]) => {
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
      setItems(parsed)
    } catch {
      setError('Could not load supplier catalog')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchCatalog() }, [])

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
    <div className="min-h-full bg-[#080808] flex flex-col">

      {/* ── Stats + search bar ── */}
      <div className="bg-[#080808]/80 backdrop-blur-xl border-b border-white/[0.06] px-4 py-3 shrink-0 sticky top-0 z-10">
        <div className="max-w-5xl mx-auto space-y-3">
          {/* Stats row */}
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-4 overflow-x-auto scrollbar-hide">
              <div className="flex items-center gap-2 shrink-0">
                <div className="w-8 h-8 bg-blue-500/10 border border-blue-500/20 rounded-xl flex items-center justify-center">
                  <Package size={14} className="text-blue-400" />
                </div>
                <div>
                  <div className="text-[10px] text-zinc-600 leading-none font-medium uppercase tracking-wider">Showing</div>
                  <div className="text-sm font-bold text-white">{filtered.length} <span className="text-zinc-600 font-normal text-xs">of {items.length}</span></div>
                </div>
              </div>
              <div className="w-px h-8 bg-white/[0.06] shrink-0" />
              <div className="flex items-center gap-2 shrink-0">
                <div className="w-8 h-8 bg-emerald-500/10 border border-emerald-500/20 rounded-xl flex items-center justify-center">
                  <DollarSign size={14} className="text-emerald-400" />
                </div>
                <div>
                  <div className="text-[10px] text-zinc-600 leading-none font-medium uppercase tracking-wider">Avg Best</div>
                  <div className="text-sm font-bold text-white">{formatCurrencyDecimal(avgBest)}</div>
                </div>
              </div>
              <div className="w-px h-8 bg-white/[0.06] shrink-0" />
              <div className="flex items-center gap-2 shrink-0">
                <div className="w-8 h-8 bg-violet-500/10 border border-violet-500/20 rounded-xl flex items-center justify-center">
                  <TrendingDown size={14} className="text-violet-400" />
                </div>
                <div>
                  <div className="text-[10px] text-zinc-600 leading-none font-medium uppercase tracking-wider">Suppliers</div>
                  <div className="text-sm font-bold text-white">Ferguson · Moore · Apex</div>
                </div>
              </div>
            </div>
            <button onClick={fetchCatalog} disabled={loading} className="shrink-0 p-2 rounded-xl hover:bg-white/[0.07] text-zinc-500 hover:text-zinc-300 transition-colors">
              <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
            </button>
          </div>

          {/* Search */}
          <div className="relative">
            <Search size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-zinc-600 pointer-events-none" />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search items…"
              className="w-full pl-9 pr-9 py-2.5 bg-white/[0.04] border border-white/[0.08] rounded-xl text-sm text-zinc-200 placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-blue-500/25 focus:border-blue-500/40 transition-all"
            />
            {search && (
              <button onClick={() => setSearch('')} className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-600 hover:text-zinc-300 transition-colors">
                <X size={14} />
              </button>
            )}
          </div>

          {/* Category tabs */}
          {categories.length > 0 && (
            <div className="flex items-center gap-1.5 overflow-x-auto scrollbar-hide pb-0.5">
              <button
                onClick={() => setActiveCategory('all')}
                className={cn(
                  'shrink-0 px-2.5 py-1 rounded-full text-[11px] font-semibold transition-all',
                  activeCategory === 'all' ? 'bg-blue-600 text-white' : 'bg-white/[0.04] text-zinc-500 hover:text-zinc-200 border border-white/[0.06]',
                )}
              >
                All
              </button>
              {categories.map(cat => (
                <button
                  key={cat}
                  onClick={() => setActiveCategory(cat)}
                  className={cn(
                    'shrink-0 px-2.5 py-1 rounded-full text-[11px] font-semibold whitespace-nowrap transition-all',
                    activeCategory === cat ? 'bg-blue-600 text-white' : 'bg-white/[0.04] text-zinc-500 hover:text-zinc-200 border border-white/[0.06]',
                  )}
                >
                  {prettyCat(cat)}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* ── Content ── */}
      <div className="max-w-5xl mx-auto px-4 py-4 w-full flex-1">

        {loading && (
          <div className="space-y-2">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="card p-4 flex items-center gap-3">
                <div className="skeleton h-4 flex-1 rounded-lg" />
                <div className="skeleton h-6 w-20 rounded-lg" />
              </div>
            ))}
          </div>
        )}

        {error && !loading && (
          <div className="card p-10 text-center">
            <p className="text-red-400 font-medium text-sm mb-3">{error}</p>
            <button onClick={fetchCatalog} className="btn-primary mx-auto">Retry</button>
          </div>
        )}

        {!loading && !error && filtered.length === 0 && (
          <div className="card p-12 text-center">
            <Package size={28} className="text-zinc-700 mx-auto mb-3" />
            <p className="text-zinc-500 font-medium text-sm">
              {search || activeCategory !== 'all' ? 'No items match your filter' : 'No catalog data available'}
            </p>
            {(search || activeCategory !== 'all') && (
              <button onClick={() => { setSearch(''); setActiveCategory('all') }} className="btn-ghost mt-3 mx-auto text-xs">
                Clear filters
              </button>
            )}
          </div>
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
                      className="card overflow-hidden"
                    >
                      <button
                        className="w-full flex items-center justify-between px-4 py-3.5 text-left"
                        onClick={() => setExpanded(isOpen ? null : item.canonical_id)}
                      >
                        <div className="flex-1 min-w-0 mr-3">
                          <div className="text-sm font-semibold text-zinc-200 truncate">{item.display_name}</div>
                          <div className="flex items-center gap-2 mt-0.5">
                            <span className="text-[11px] text-emerald-400 font-semibold flex items-center gap-0.5">
                              <TrendingDown size={11} />
                              {formatCurrencyDecimal(item.best_price)}
                            </span>
                            <span className="text-[11px] text-zinc-600">{SUPPLIER_LABELS[item.best_supplier] ?? item.best_supplier}</span>
                          </div>
                        </div>
                        {isOpen ? <ChevronUp size={15} className="text-zinc-600 shrink-0" /> : <ChevronDown size={15} className="text-zinc-600 shrink-0" />}
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
                            <div className="border-t border-white/[0.06] divide-y divide-white/[0.05]">
                              {suppliers.map(sup => {
                                const p = item.prices?.[sup as keyof typeof item.prices]
                                if (!p) return null
                                const isBest = sup === item.best_supplier
                                return (
                                  <div key={sup} className={cn('flex items-center justify-between px-4 py-3', isBest && 'bg-emerald-500/[0.04]')}>
                                    <div>
                                      <div className={cn('text-xs font-semibold flex items-center gap-1.5', isBest ? 'text-emerald-400' : 'text-zinc-300')}>
                                        {SUPPLIER_LABELS[sup]}
                                        {isBest && <span className="px-1.5 py-px bg-emerald-500/10 text-emerald-400 text-[9px] rounded-full border border-emerald-500/20 font-bold">BEST</span>}
                                      </div>
                                      <div className="text-[11px] text-zinc-600 font-mono mt-0.5">{p.sku}</div>
                                    </div>
                                    <div className={cn('text-sm font-bold tabular-nums', isBest ? 'text-emerald-400' : 'text-zinc-400')}>
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
                  <tr className="border-b border-white/[0.06] bg-[#0f0f0f]">
                    <th className="px-4 py-3 text-left text-[10px] font-bold text-zinc-600 uppercase tracking-widest">Item</th>
                    <th className="px-4 py-3 text-right text-[10px] font-bold text-zinc-600 uppercase tracking-widest">Ferguson</th>
                    <th className="px-4 py-3 text-right text-[10px] font-bold text-zinc-600 uppercase tracking-widest">Moore Supply</th>
                    <th className="px-4 py-3 text-right text-[10px] font-bold text-zinc-600 uppercase tracking-widest">Apex</th>
                    <th className="px-4 py-3 text-right text-[10px] font-bold text-emerald-600 uppercase tracking-widest">Best Price</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.05]">
                  <AnimatePresence initial={false}>
                    {filtered.map(item => (
                      <motion.tr
                        key={item.canonical_id}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="hover:bg-white/[0.025] transition-colors"
                      >
                        <td className="px-4 py-3 font-medium text-zinc-200">{item.display_name}</td>
                        {suppliers.map(sup => {
                          const p = item.prices?.[sup as keyof typeof item.prices]
                          const isBest = sup === item.best_supplier
                          return (
                            <td key={sup} className={cn('px-4 py-3 text-right tabular-nums', isBest ? 'text-emerald-400 font-semibold' : 'text-zinc-500')}>
                              {p ? formatCurrencyDecimal(p.cost) : <span className="text-zinc-700">—</span>}
                            </td>
                          )
                        })}
                        <td className="px-4 py-3 text-right">
                          <span className="inline-flex items-center gap-1 px-2 py-1 bg-emerald-500/10 text-emerald-400 text-xs font-bold rounded-lg border border-emerald-500/20 tabular-nums">
                            <TrendingDown size={10} />
                            {formatCurrencyDecimal(item.best_price)}
                          </span>
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
  )
}
