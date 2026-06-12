'use client'

import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDown, ChevronUp, TrendingDown, History, Copy, Check } from 'lucide-react'
import { cn, formatCurrencyDecimal } from '@/lib/utils'
import { Badge } from '@/components/ui/Badge'
import { Tooltip } from '@/components/ui/Tooltip'
import { PriceChangeIndicator } from './PriceChangeIndicator'
import type { CatalogItem, SupplierPrice } from '@/lib/hooks'

interface SupplierItemCardProps {
  item: CatalogItem
  isOpen: boolean
  onToggle: () => void
  onHistory: (item: CatalogItem) => void
  onCopySku: (sku: string) => void
  copiedSku: string | null
  suppliers: string[]
  supplierLabels: Record<string, string>
}

export function SupplierItemCard({
  item,
  isOpen,
  onToggle,
  onHistory,
  onCopySku,
  copiedSku,
  suppliers,
  supplierLabels,
}: SupplierItemCardProps) {
  return (
    <motion.div
      layout
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="card overflow-hidden transition-all hover:-translate-y-0.5 hover:shadow-lg"
    >
      <button
        className="flex w-full items-center justify-between px-4 py-3.5 text-left"
        onClick={onToggle}
      >
        <div className="mr-3 min-w-0 flex-1">
          <h3 className="truncate text-sm font-semibold text-[color:var(--ink)]">{item.display_name}</h3>
          <div className="mt-0.5 flex items-center gap-2">
            <Badge variant="success" size="sm" dot>
              <TrendingDown size={10} />
              {formatCurrencyDecimal(item.best_price)}
            </Badge>
            <span className="text-[11px] text-[color:var(--muted-ink)]">{supplierLabels[item.best_supplier] ?? item.best_supplier}</span>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Tooltip content="View price history">
            <button
              onClick={e => { e.stopPropagation(); onHistory(item) }}
              className="flex min-h-[28px] min-w-[28px] items-center justify-center rounded-lg p-1.5 text-[color:var(--muted-ink)] transition-colors hover:bg-[color:var(--panel-strong)] hover:text-[color:var(--ink)]"
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
            <div className="divide-y divide-[color:var(--line)] border-t border-[color:var(--line)]">
              {suppliers.map(sup => {
                const p = item.prices?.[sup as keyof typeof item.prices] as SupplierPrice | undefined
                if (!p) return null
                const isBest = sup === item.best_supplier
                return (
                  <div key={sup} className={cn('flex items-center justify-between px-4 py-3', isBest && 'bg-emerald-500/[0.04]')}>
                    <div>
                      <div className={cn('flex items-center gap-1.5 text-xs font-semibold', isBest ? 'text-emerald-700' : 'text-[color:var(--ink)]')}>
                        {supplierLabels[sup]}
                        {isBest && <Badge variant="success" size="sm">BEST</Badge>}
                      </div>
                      <div className="mt-0.5 flex items-center gap-1.5">
                        <span className="font-mono text-[11px] text-[color:var(--muted-ink)]">{p.sku}</span>
                        <Tooltip content="Copy SKU">
                          <button
                            onClick={e => { e.stopPropagation(); onCopySku(p.sku) }}
                            className="flex min-h-[28px] min-w-[28px] items-center justify-center rounded-lg p-1.5 text-[color:var(--muted-ink)] transition-colors hover:bg-[color:var(--panel-strong)] hover:text-[color:var(--ink)]"
                            aria-label={`Copy SKU ${p.sku}`}
                          >
                            {copiedSku === p.sku ? <Check size={12} className="text-emerald-600" /> : <Copy size={12} />}
                          </button>
                        </Tooltip>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <PriceChangeIndicator changePct={p.change_pct} />
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
}
