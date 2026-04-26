'use client'

import { useState, useMemo, useCallback } from 'react'
import { motion } from 'framer-motion'
import { FileText, Brain, Award, Info } from 'lucide-react'
import { Badge } from '@/components/ui/Badge'
import { DataTable, type Column } from '@/components/ui/DataTable'
import { Tooltip } from '@/components/ui/Tooltip'
import { formatCurrencyDecimal } from '@/lib/utils'
import { WhyThisPriceModal } from './WhyThisPriceModal'

export interface LineItem {
  line_type: string
  description: string
  quantity: number
  unit: string
  unit_cost: number
  total_cost: number
  supplier?: string | null
  sku?: string | null
  canonical_item?: string | null
  trace_json?: {
    rag_sources?: Array<{
      doc_id: number
      doc_name: string
      score: number
      chunk_idx: number
    }>
    memory_hits?: Array<{
      id: number
      kind: string
      score: number | null
    }>
    similar_outcomes?: Array<{
      estimate_id: number
      outcome: string
      price: number | null
    }>
    [key: string]: unknown
  } | null
}

const LINE_TYPE_LABEL: Record<string, string> = {
  labor: 'Labor',
  material: 'Material',
  markup: 'Markup',
  tax: 'Tax',
  misc: 'Misc',
}

const LINE_TYPE_VARIANT: Record<string, 'success' | 'warning' | 'danger' | 'info' | 'neutral' | 'accent'> = {
  labor:    'info',
  material: 'success',
  markup:   'warning',
  tax:      'neutral',
  misc:     'info',
}

export interface LineItemsTableProps {
  lineItems: LineItem[]
  subtotal: number
  taxTotal: number
  taxRate: number
  grandTotal: number
}

type SortKey = 'description' | 'quantity' | 'unit_cost' | 'total_cost'

export function LineItemsTable({
  lineItems,
  subtotal,
  taxTotal,
  taxRate,
  grandTotal,
}: LineItemsTableProps) {
  const [sortKey, setSortKey] = useState<SortKey | undefined>(undefined)
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')
  const [whyItem, setWhyItem] = useState<LineItem | null>(null)

  const laborLines    = useMemo(() => lineItems.filter(l => l.line_type === 'labor'), [lineItems])
  const materialLines = useMemo(() => lineItems.filter(l => l.line_type === 'material'), [lineItems])
  const otherLines    = useMemo(() => lineItems.filter(l => !['labor', 'material'].includes(l.line_type)), [lineItems])

  const handleSort = useCallback((key: string) => {
    if (sortKey === key) {
      setSortDir(prev => (prev === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key as SortKey)
      setSortDir('asc')
    }
  }, [sortKey])

  const sortItems = useCallback((items: LineItem[]) => {
    if (!sortKey) return items
    return [...items].sort((a, b) => {
      const aVal = a[sortKey]
      const bVal = b[sortKey]
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortDir === 'asc' ? aVal - bVal : bVal - aVal
      }
      return sortDir === 'asc'
        ? String(aVal).localeCompare(String(bVal))
        : String(bVal).localeCompare(String(aVal))
    })
  }, [sortKey, sortDir])

  const columns: Column<LineItem>[] = useMemo(() => [
    {
      key: 'description',
      header: 'Description',
      sortable: true,
      render: (item) => (
        <div className="min-w-0">
          <div className="text-sm text-[color:var(--foreground)] font-medium">{item.description}</div>
          <div className="flex items-center gap-3 mt-1 flex-wrap">
            {item.supplier && (
              <span className="text-[10px] text-[color:var(--muted-ink)]">{item.supplier}</span>
            )}
            {item.sku && (
              <span className="text-[10px] text-[color:var(--muted-ink)] font-mono">SKU: {item.sku}</span>
            )}
            <Badge variant={LINE_TYPE_VARIANT[item.line_type] ?? 'neutral'} size="sm">
              {LINE_TYPE_LABEL[item.line_type] ?? item.line_type}
            </Badge>
            {(item.trace_json?.rag_sources?.length ?? 0) > 0 && (
              <Tooltip
                content={
                  `Source: ${item.trace_json!.rag_sources![0].doc_name}` +
                  (item.trace_json!.rag_sources!.length > 1
                    ? ` +${item.trace_json!.rag_sources!.length - 1} more`
                    : '')
                }
              >
                <span className="inline-flex items-center gap-1 text-xs text-[color:var(--muted-ink)] cursor-help">
                  <FileText size={10} />
                  {item.trace_json!.rag_sources![0].doc_name.length > 20
                    ? `${item.trace_json!.rag_sources![0].doc_name.slice(0, 20)}…`
                    : item.trace_json!.rag_sources![0].doc_name}
                </span>
              </Tooltip>
            )}
            {(item.trace_json?.memory_hits?.length ?? 0) > 0 && (
              <Tooltip
                content={`Used ${item.trace_json!.memory_hits!.length} learned fact(s) about your business`}
              >
                <span className="inline-flex items-center gap-1 text-xs text-[color:var(--muted-ink)] cursor-help">
                  <Brain size={10} />
                  memory ×{item.trace_json!.memory_hits!.length}
                </span>
              </Tooltip>
            )}
            {(item.trace_json?.similar_outcomes?.length ?? 0) > 0 && (() => {
              const outs = item.trace_json!.similar_outcomes!
              const won = outs.filter(o => o.outcome === 'won').length
              return (
                <Tooltip
                  content={
                    `${outs.length} similar past job${outs.length > 1 ? 's' : ''} — ${won} won` +
                    outs.slice(0, 3)
                      .map(o => `\n• ${o.outcome}${o.price ? ` $${Math.round(o.price).toLocaleString()}` : ''}`)
                      .join('')
                  }
                >
                  <span className="inline-flex items-center gap-1 text-xs text-[color:var(--muted-ink)] cursor-help">
                    <Award size={10} />
                    {won}/{outs.length} won
                  </span>
                </Tooltip>
              )
            })()}
            <button
              type="button"
              onClick={() => setWhyItem(item)}
              className="inline-flex items-center gap-1 text-xs text-[color:var(--muted-ink)] hover:text-[color:var(--accent)] transition-colors"
              aria-label="Why this price?"
            >
              <Info size={11} />
              Why?
            </button>
          </div>
        </div>
      ),
    },
    {
      key: 'quantity',
      header: 'Qty',
      sortable: true,
      align: 'right' as const,
      width: '80px',
      render: (item) => (
        <span className="text-sm tabular-nums">
          {item.quantity} {item.unit !== 'each' ? item.unit : ''}
        </span>
      ),
    },
    {
      key: 'unit_cost',
      header: 'Unit Cost',
      sortable: true,
      align: 'right' as const,
      width: '110px',
      render: (item) => (
        <span className="text-sm tabular-nums">{formatCurrencyDecimal(item.unit_cost)}</span>
      ),
    },
    {
      key: 'total_cost',
      header: 'Total',
      sortable: true,
      align: 'right' as const,
      width: '110px',
      render: (item) => (
        <span className="text-sm font-semibold text-[color:var(--ink)] tabular-nums">
          {formatCurrencyDecimal(item.total_cost)}
        </span>
      ),
    },
  ], [])

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, delay: 0.1 }}
      className="card overflow-hidden"
    >
      <div className="px-4 py-3 border-b border-white/[0.06] flex items-center justify-between">
        <h2 className="text-xs font-bold text-[color:var(--ink)] uppercase tracking-wider">Line Items</h2>
        <span className="text-[11px] text-[color:var(--muted-ink)]">{lineItems.length} {lineItems.length === 1 ? 'item' : 'items'}</span>
      </div>

      {laborLines.length > 0 && (
        <LineItemSection title="Labor">
          <DataTable
            columns={columns}
            data={sortItems(laborLines)}
            keyExtractor={(item) => `labor-${item.description}-${item.unit_cost}`}
            sortKey={sortKey}
            sortDir={sortDir}
            onSort={handleSort}
            className="[&_.hidden.lg\\:block]:!block [&_.lg\\:hidden]:!hidden [&_>div]:!border-0 [&_>div]:!rounded-none [&_>div]:!shadow-none"
          />
        </LineItemSection>
      )}

      {materialLines.length > 0 && (
        <LineItemSection title="Materials">
          <DataTable
            columns={columns}
            data={sortItems(materialLines)}
            keyExtractor={(item) => `material-${item.description}-${item.unit_cost}`}
            sortKey={sortKey}
            sortDir={sortDir}
            onSort={handleSort}
            className="[&_.hidden.lg\\:block]:!block [&_.lg\\:hidden]:!hidden [&_>div]:!border-0 [&_>div]:!rounded-none [&_>div]:!shadow-none"
          />
        </LineItemSection>
      )}

      {otherLines.length > 0 && (
        <LineItemSection title="Fees & Taxes">
          <DataTable
            columns={columns}
            data={sortItems(otherLines)}
            keyExtractor={(item) => `other-${item.description}-${item.unit_cost}`}
            sortKey={sortKey}
            sortDir={sortDir}
            onSort={handleSort}
            className="[&_.hidden.lg\\:block]:!block [&_.lg\\:hidden]:!hidden [&_>div]:!border-0 [&_>div]:!rounded-none [&_>div]:!shadow-none"
          />
        </LineItemSection>
      )}

      {/* Totals footer */}
      <div className="bg-white/[0.02] border-t border-white/[0.06] divide-y divide-white/[0.04]">
        {[
          { label: 'Subtotal',  value: subtotal },
          { label: `Tax (${(taxRate * 100).toFixed(2)}%)`, value: taxTotal },
        ].map(({ label, value }) => (
          <div key={label} className="flex items-center justify-between px-5 py-2.5 text-sm">
            <span className="text-[color:var(--muted-ink)]">{label}</span>
            <span className="text-[color:var(--foreground)] font-semibold tabular-nums">{formatCurrencyDecimal(value)}</span>
          </div>
        ))}
        <div className="flex items-center justify-between px-5 py-3">
          <span className="text-sm font-bold text-[color:var(--ink)]">Grand Total</span>
          <span className="text-xl font-extrabold text-[color:var(--ink)] tabular-nums">{formatCurrencyDecimal(grandTotal)}</span>
        </div>
      </div>
      <WhyThisPriceModal item={whyItem} onClose={() => setWhyItem(null)} />
    </motion.div>
  )
}

function LineItemSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="px-4 py-2 bg-white/[0.015] border-y border-white/[0.04]">
        <span className="text-[10px] font-bold text-[color:var(--muted-ink)] uppercase tracking-widest">{title}</span>
      </div>
      {children}
    </div>
  )
}
