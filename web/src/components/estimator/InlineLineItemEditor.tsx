'use client'

import { useState, useCallback, useMemo } from 'react'
import { Plus, Trash2, Save, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { formatCurrencyDecimal } from '@/lib/utils'
import { Badge } from '@/components/ui/Badge'
import type { LineItem } from '@/types'

interface InlineLineItemEditorProps {
  lineItems: LineItem[]
  estimateId?: number | null
  onSave: (lineItems: LineItem[]) => void
  onCancel: () => void
}

const LINE_TYPES = ['labor', 'material', 'markup', 'tax', 'misc'] as const
const UNITS = ['each', 'hr', 'lf', 'sq ft', 'lb', 'gal', 'lot', 'job'] as const

const lineTypeBadge = (type: string): 'info' | 'success' | 'warning' | 'neutral' => {
  switch (type) {
    case 'labor': return 'info'
    case 'material': return 'success'
    case 'markup': return 'warning'
    case 'tax': case 'misc': return 'neutral'
    default: return 'neutral'
  }
}

function createEmptyLineItem(): LineItem {
  return {
    line_type: 'material',
    description: '',
    quantity: 1,
    unit: 'each',
    unit_cost: 0,
    total_cost: 0,
  }
}

export function InlineLineItemEditor({
  lineItems: initialItems,
  onSave,
  onCancel,
}: InlineLineItemEditorProps) {
  const [items, setItems] = useState<LineItem[]>(() =>
    initialItems.map(item => ({ ...item }))
  )
  const [saving, setSaving] = useState(false)

  const updateItem = useCallback((index: number, field: keyof LineItem, value: string | number) => {
    setItems(prev => {
      const next = [...prev]
      const item = { ...next[index] }

      if (field === 'quantity' || field === 'unit_cost') {
        const numVal = typeof value === 'string' ? parseFloat(value) || 0 : value
        ;(item[field] as number) = numVal
        item.total_cost = item.quantity * item.unit_cost
      } else {
        ;(item[field] as string) = String(value)
      }

      next[index] = item
      return next
    })
  }, [])

  const addRow = useCallback(() => {
    setItems(prev => [...prev, createEmptyLineItem()])
  }, [])

  const removeRow = useCallback((index: number) => {
    setItems(prev => prev.filter((_, i) => i !== index))
  }, [])

  const handleSave = useCallback(async () => {
    setSaving(true)
    try {
      // Recompute totals before saving
      const computed = items.map(item => ({
        ...item,
        total_cost: item.quantity * item.unit_cost,
      }))
      onSave(computed)
    } finally {
      setSaving(false)
    }
  }, [items, onSave])

  const grandTotal = useMemo(
    () => items.reduce((sum, item) => sum + item.quantity * item.unit_cost, 0),
    [items]
  )

  const hasChanges = useMemo(() => {
    if (items.length !== initialItems.length) return true
    return items.some((item, i) => {
      const orig = initialItems[i]
      return (
        item.description !== orig.description ||
        item.quantity !== orig.quantity ||
        item.unit !== orig.unit ||
        item.unit_cost !== orig.unit_cost ||
        item.line_type !== orig.line_type
      )
    })
  }, [items, initialItems])

  return (
    <div className="mt-3 rounded-xl border border-[color:var(--line)] bg-[color:var(--panel)] overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[color:var(--line)] bg-[color:var(--panel-strong)] px-3 py-2">
        <span className="text-xs font-semibold text-[color:var(--ink)]">
          Edit Line Items
        </span>
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={addRow}
            className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-[10px] font-semibold text-[color:var(--accent-strong)] transition-colors hover:bg-[color:var(--accent-soft)]"
          >
            <Plus size={11} />
            Add Row
          </button>
        </div>
      </div>

      {/* Table — horizontal scroll on mobile */}
      <div className="overflow-x-auto">
        <table className="w-full min-w-[600px] text-xs">
          <thead>
            <tr className="border-b border-[color:var(--line)] bg-[color:var(--panel-strong)]/50">
              <th className="px-2 py-1.5 text-left font-medium text-[color:var(--muted-ink)] w-[80px]">Type</th>
              <th className="px-2 py-1.5 text-left font-medium text-[color:var(--muted-ink)]">Description</th>
              <th className="px-2 py-1.5 text-right font-medium text-[color:var(--muted-ink)] w-[64px]">Qty</th>
              <th className="px-2 py-1.5 text-left font-medium text-[color:var(--muted-ink)] w-[72px]">Unit</th>
              <th className="px-2 py-1.5 text-right font-medium text-[color:var(--muted-ink)] w-[90px]">Unit Cost</th>
              <th className="px-2 py-1.5 text-right font-medium text-[color:var(--muted-ink)] w-[90px]">Total</th>
              <th className="w-[36px]" />
            </tr>
          </thead>
          <tbody>
            {items.map((item, index) => (
              <tr
                key={index}
                className="border-b border-[color:var(--line)]/50 transition-colors hover:bg-[color:var(--panel-strong)]/30"
              >
                <td className="px-2 py-1">
                  <select
                    value={item.line_type}
                    onChange={e => updateItem(index, 'line_type', e.target.value)}
                    className="w-full rounded-lg border border-[color:var(--line)] bg-[color:var(--panel)] px-1.5 py-1 text-[11px] text-[color:var(--ink)] outline-none focus:border-[color:var(--accent)]"
                  >
                    {LINE_TYPES.map(t => (
                      <option key={t} value={t}>{t}</option>
                    ))}
                  </select>
                </td>
                <td className="px-2 py-1">
                  <input
                    type="text"
                    value={item.description}
                    onChange={e => updateItem(index, 'description', e.target.value)}
                    placeholder="Item description"
                    className="w-full rounded-lg border border-[color:var(--line)] bg-[color:var(--panel)] px-2 py-1 text-[11px] text-[color:var(--ink)] placeholder:text-[color:var(--muted-ink)] outline-none focus:border-[color:var(--accent)]"
                  />
                </td>
                <td className="px-2 py-1">
                  <input
                    type="number"
                    min={0}
                    step="0.01"
                    value={item.quantity}
                    onChange={e => updateItem(index, 'quantity', e.target.value)}
                    className="w-full rounded-lg border border-[color:var(--line)] bg-[color:var(--panel)] px-2 py-1 text-right text-[11px] text-[color:var(--ink)] outline-none focus:border-[color:var(--accent)] [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
                  />
                </td>
                <td className="px-2 py-1">
                  <select
                    value={item.unit}
                    onChange={e => updateItem(index, 'unit', e.target.value)}
                    className="w-full rounded-lg border border-[color:var(--line)] bg-[color:var(--panel)] px-1.5 py-1 text-[11px] text-[color:var(--ink)] outline-none focus:border-[color:var(--accent)]"
                  >
                    {UNITS.map(u => (
                      <option key={u} value={u}>{u}</option>
                    ))}
                    {/* Allow existing values not in the preset list */}
                    {!UNITS.includes(item.unit as typeof UNITS[number]) && (
                      <option value={item.unit}>{item.unit}</option>
                    )}
                  </select>
                </td>
                <td className="px-2 py-1">
                  <input
                    type="number"
                    min={0}
                    step="0.01"
                    value={item.unit_cost}
                    onChange={e => updateItem(index, 'unit_cost', e.target.value)}
                    className="w-full rounded-lg border border-[color:var(--line)] bg-[color:var(--panel)] px-2 py-1 text-right text-[11px] text-[color:var(--ink)] outline-none focus:border-[color:var(--accent)] [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
                  />
                </td>
                <td className="px-2 py-1 text-right">
                  <span className="text-[11px] font-medium text-[color:var(--ink)]">
                    {formatCurrencyDecimal(item.quantity * item.unit_cost)}
                  </span>
                </td>
                <td className="px-1 py-1">
                  <button
                    type="button"
                    onClick={() => removeRow(index)}
                    className="rounded-lg p-1.5 text-[color:var(--muted-ink)] transition-colors hover:bg-[hsl(var(--danger)/0.1)] hover:text-[hsl(var(--danger))]"
                    aria-label={`Remove ${item.description || 'row'}`}
                  >
                    <Trash2 size={12} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Footer with totals + actions */}
      <div className="flex items-center justify-between border-t border-[color:var(--line)] bg-[color:var(--panel-strong)] px-3 py-2">
        <div className="flex items-center gap-3">
          <span className="text-xs text-[color:var(--muted-ink)]">
            {items.length} item{items.length !== 1 ? 's' : ''}
          </span>
          <div className="flex gap-1">
            {(['labor', 'material', 'markup'] as const).map(type => {
              const count = items.filter(i => i.line_type === type).length
              if (!count) return null
              return (
                <Badge key={type} variant={lineTypeBadge(type)} size="sm">
                  {count} {type}
                </Badge>
              )
            })}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-[color:var(--ink)]">
            Total: {formatCurrencyDecimal(grandTotal)}
          </span>
          <button
            type="button"
            onClick={onCancel}
            className={cn(
              'inline-flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-[11px] font-semibold transition-colors',
              'text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] hover:bg-[color:var(--panel)]'
            )}
          >
            <X size={11} />
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={saving || !hasChanges}
            className={cn(
              'inline-flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-[11px] font-semibold transition-colors',
              'bg-[color:var(--accent)] text-white hover:bg-[color:var(--accent-strong)]',
              'disabled:opacity-40 disabled:cursor-not-allowed'
            )}
          >
            <Save size={11} />
            {saving ? 'Saving…' : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>
  )
}
