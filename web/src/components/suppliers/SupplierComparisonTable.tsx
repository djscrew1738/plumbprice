'use client'

import { motion, AnimatePresence } from 'framer-motion'
import { TrendingDown, History } from 'lucide-react'
import { cn, formatCurrencyDecimal } from '@/lib/utils'
import { Badge } from '@/components/ui/Badge'
import { Tooltip } from '@/components/ui/Tooltip'
import { PriceChangeIndicator } from './PriceChangeIndicator'
import type { CatalogItem, SupplierPrice } from '@/lib/hooks'

interface SupplierComparisonTableProps {
  items: CatalogItem[]
  suppliers: string[]
  supplierLabels: Record<string, string>
  onHistory: (item: CatalogItem) => void
}

export function SupplierComparisonTable({ items, suppliers, supplierLabels, onHistory }: SupplierComparisonTableProps) {
  return (
    <div className="card overflow-hidden">
      <table className="w-full text-sm">
        <thead className="sticky top-0">
          <tr className="border-b border-[color:var(--line)] bg-[color:var(--panel-strong)]">
            <th className="px-4 py-3 text-left text-[10px] font-bold uppercase tracking-widest text-[color:var(--muted-ink)]">Item</th>
            {suppliers.map(sup => (
              <th key={sup} className="px-4 py-3 text-right text-[10px] font-bold uppercase tracking-widest text-[color:var(--muted-ink)]">
                {supplierLabels[sup] ?? sup}
              </th>
            ))}
            <th className="px-4 py-3 text-right text-[10px] font-bold uppercase tracking-widest text-[hsl(var(--success))]">Best Price</th>
            <th className="w-10" />
          </tr>
        </thead>
        <tbody className="divide-y divide-[color:var(--line)]">
          <AnimatePresence initial={false}>
            {items.map(item => (
              <motion.tr
                key={item.canonical_id}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="transition-all hover:-translate-y-0.5 hover:bg-[color:var(--panel-strong)]"
              >
                <td className="px-4 py-3 font-medium text-[color:var(--ink)]">{item.display_name}</td>
                {suppliers.map(sup => {
                  const p = item.prices?.[sup as keyof typeof item.prices] as SupplierPrice | undefined
                  const isBest = sup === item.best_supplier
                  return (
                    <td key={sup} className={cn('px-4 py-3 text-right', isBest ? 'font-semibold text-[hsl(var(--success))]' : 'text-[color:var(--muted-ink)]')}>
                      {p ? (
                        <span className="inline-flex items-center gap-1.5 tabular-nums">
                          <PriceChangeIndicator changePct={p.change_pct} />
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
                      onClick={() => onHistory(item)}
                      className="flex min-h-[28px] min-w-[28px] items-center justify-center rounded-lg p-1.5 text-[color:var(--muted-ink)] transition-colors hover:bg-[color:var(--panel-strong)] hover:text-[color:var(--ink)]"
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
  )
}
