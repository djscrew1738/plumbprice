'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { RefreshCw, TrendingDown, Package, DollarSign, ChevronDown, ChevronUp } from 'lucide-react'
import { cn, formatCurrencyDecimal } from '@/lib/utils'
import axios from 'axios'

interface SupplierPrice {
  name: string
  sku: string
  cost: number
}
interface CatalogItem {
  canonical_id: string
  display_name: string
  category: string
  best_price: number
  best_supplier: string
  prices: {
    ferguson?: SupplierPrice
    moore_supply?: SupplierPrice
    apex?: SupplierPrice
  }
}

const API = process.env.NEXT_PUBLIC_API_URL + '/api/v1'
const SUPPLIER_LABELS: Record<string, string> = {
  ferguson: 'Ferguson',
  moore_supply: 'Moore Supply',
  apex: 'Apex',
}

export function SuppliersPage() {
  const [items, setItems] = useState<CatalogItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expanded, setExpanded] = useState<string | null>(null)

  const fetchCatalog = async () => {
    try {
      setLoading(true)
      setError(null)
      const res = await axios.get(`${API}/suppliers/catalog`)
      const raw: Record<string, Record<string, { sku: string; name: string; cost: number }>> =
        res.data?.items ?? res.data ?? {}
      const parsed: CatalogItem[] = Object.entries(raw).map(([canonical_id, prices]) => {
        const entries = Object.entries(prices) as [string, { sku: string; name: string; cost: number }][]
        let best_supplier = entries[0]?.[0] ?? ''
        let best_price = entries[0]?.[1]?.cost ?? 0
        for (const [sup, p] of entries) {
          if (p.cost < best_price) { best_price = p.cost; best_supplier = sup }
        }
        return {
          canonical_id,
          display_name: canonical_id.replace(/\./g, ' > ').replace(/_/g, ' '),
          category: canonical_id.split('.')[0],
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

  const avgBest = items.length > 0
    ? items.reduce((s, i) => s + i.best_price, 0) / items.length
    : 0

  const suppliers = ['ferguson', 'moore_supply', 'apex']

  return (
    <div className="min-h-full bg-[#0a0a0a]">
      {/* Stats bar */}
      <div className="bg-black/40 backdrop-blur-xl border-b border-white/5 px-4 py-3">
        <div className="max-w-5xl mx-auto flex items-center justify-between gap-4">
          <div className="flex items-center gap-4 overflow-x-auto scrollbar-hide">
            <div className="flex items-center gap-2 shrink-0">
              <div className="w-8 h-8 bg-blue-500/10 border border-blue-500/20 rounded-xl flex items-center justify-center">
                <Package size={15} className="text-blue-400" />
              </div>
              <div>
                <div className="text-[11px] text-zinc-500 leading-none">Items</div>
                <div className="text-sm font-bold text-white">{items.length}</div>
              </div>
            </div>
            <div className="w-px h-8 bg-white/[0.06] shrink-0" />
            <div className="flex items-center gap-2 shrink-0">
              <div className="w-8 h-8 bg-emerald-500/10 border border-emerald-500/20 rounded-xl flex items-center justify-center">
                <DollarSign size={15} className="text-emerald-400" />
              </div>
              <div>
                <div className="text-[11px] text-zinc-500 leading-none">Avg Best Price</div>
                <div className="text-sm font-bold text-white">{formatCurrencyDecimal(avgBest)}</div>
              </div>
            </div>
            <div className="w-px h-8 bg-white/[0.06] shrink-0" />
            <div className="flex items-center gap-2 shrink-0">
              <div className="w-8 h-8 bg-violet-500/10 border border-violet-500/20 rounded-xl flex items-center justify-center">
                <TrendingDown size={15} className="text-violet-400" />
              </div>
              <div>
                <div className="text-[11px] text-zinc-500 leading-none">Suppliers</div>
                <div className="text-sm font-bold text-white">Ferguson . Moore . Apex</div>
              </div>
            </div>
          </div>
          <button
            onClick={fetchCatalog}
            disabled={loading}
            className="shrink-0 p-2 rounded-xl hover:bg-white/10 text-zinc-400 transition-colors"
          >
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 py-4">
        {loading && (
          <div className="space-y-2.5">
            {Array.from({ length: 10 }).map((_, i) => (
              <div key={i} className="card p-4 flex items-center gap-3">
                <div className="skeleton h-4 flex-1 rounded-lg" />
                <div className="skeleton h-6 w-16 rounded-lg" />
              </div>
            ))}
          </div>
        )}

        {error && !loading && (
          <div className="card p-8 text-center">
            <p className="text-red-400 font-medium mb-3">{error}</p>
            <button onClick={fetchCatalog} className="btn-primary text-sm">Retry</button>
          </div>
        )}

        {!loading && !error && items.length === 0 && (
          <div className="card p-10 text-center">
            <Package size={32} className="text-zinc-600 mx-auto mb-3" />
            <p className="text-zinc-400 font-medium">No catalog data available</p>
          </div>
        )}

        {!loading && !error && items.length > 0 && (
          <>
            {/* Mobile: expandable cards */}
            <div className="space-y-2 lg:hidden">
              {items.map((item, i) => {
                const isOpen = expanded === item.canonical_id
                return (
                  <motion.div
                    key={item.canonical_id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.2, delay: i * 0.02 }}
                    className="card overflow-hidden"
                  >
                    <button
                      className="w-full flex items-center justify-between px-4 py-3.5 text-left"
                      onClick={() => setExpanded(isOpen ? null : item.canonical_id)}
                    >
                      <div className="flex-1 min-w-0 mr-3">
                        <div className="text-sm font-semibold text-zinc-200 truncate">
                          {item.display_name ?? item.canonical_id.replace(/_/g, ' ')}
                        </div>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-[11px] text-emerald-400 font-semibold flex items-center gap-0.5">
                            <TrendingDown size={11} />
                            Best: {formatCurrencyDecimal(item.best_price)}
                          </span>
                          <span className="text-[11px] text-zinc-500">
                            {SUPPLIER_LABELS[item.best_supplier] ?? item.best_supplier}
                          </span>
                        </div>
                      </div>
                      {isOpen ? <ChevronUp size={16} className="text-zinc-500 shrink-0" /> : <ChevronDown size={16} className="text-zinc-500 shrink-0" />}
                    </button>

                    {isOpen && (
                      <div className="border-t border-white/5 divide-y divide-white/5">
                        {suppliers.map(sup => {
                          const p = item.prices?.[sup as keyof typeof item.prices]
                          if (!p) return null
                          const isBest = sup === item.best_supplier
                          return (
                            <div key={sup} className={cn('flex items-center justify-between px-4 py-3', isBest && 'bg-emerald-500/5')}>
                              <div>
                                <div className={cn('text-xs font-semibold', isBest ? 'text-emerald-400' : 'text-zinc-300')}>
                                  {SUPPLIER_LABELS[sup]}
                                  {isBest && <span className="ml-1.5 px-1.5 py-0.5 bg-emerald-500/10 text-emerald-400 text-[10px] rounded-full border border-emerald-500/20">Best</span>}
                                </div>
                                <div className="text-[11px] text-zinc-500 font-mono mt-0.5">{p.sku}</div>
                              </div>
                              <div className={cn('text-sm font-bold', isBest ? 'text-emerald-400' : 'text-zinc-300')}>
                                {formatCurrencyDecimal(p.cost)}
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    )}
                  </motion.div>
                )
              })}
            </div>

            {/* Desktop table */}
            <div className="hidden lg:block card overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/5 bg-white/[0.02]">
                    <th className="px-4 py-3 text-left text-xs font-semibold text-zinc-500 uppercase tracking-wider">Item</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-zinc-500 uppercase tracking-wider">Ferguson</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-zinc-500 uppercase tracking-wider">Moore Supply</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-zinc-500 uppercase tracking-wider">Apex</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-emerald-400 uppercase tracking-wider">Best Price</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {items.map((item, i) => (
                    <motion.tr
                      key={item.canonical_id}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ duration: 0.15, delay: i * 0.02 }}
                      className="hover:bg-white/[0.03] transition-colors"
                    >
                      <td className="px-4 py-3 font-medium text-white">
                        {item.display_name ?? item.canonical_id.replace(/_/g, ' ')}
                      </td>
                      {suppliers.map(sup => {
                        const p = item.prices?.[sup as keyof typeof item.prices]
                        const isBest = sup === item.best_supplier
                        return (
                          <td key={sup} className={cn('px-4 py-3 text-right', isBest ? 'text-emerald-400 font-bold' : 'text-zinc-400')}>
                            {p ? formatCurrencyDecimal(p.cost) : '--'}
                          </td>
                        )
                      })}
                      <td className="px-4 py-3 text-right">
                        <span className="inline-flex items-center gap-1 px-2 py-1 bg-emerald-500/10 text-emerald-400 text-xs font-bold rounded-lg border border-emerald-500/20">
                          <TrendingDown size={11} />
                          {formatCurrencyDecimal(item.best_price)}
                        </span>
                      </td>
                    </motion.tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
