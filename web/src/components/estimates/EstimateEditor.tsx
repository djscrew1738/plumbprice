'use client'

import { useMemo, useState } from 'react'
import { Plus, Save, Trash2, X } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import { estimatesApi } from '@/lib/api'
import { useToast } from '@/components/ui/Toast'
import { formatCurrencyDecimal } from '@/lib/utils'
import type { LineItem } from './LineItemsTable'

const LINE_TYPES = ['labor', 'material', 'markup', 'tax', 'misc', 'trip', 'permit'] as const

interface EditableLine extends LineItem {
  _key: string
}

export interface EstimateEditorProps {
  estimateId: number
  initialLineItems: LineItem[]
  taxRate: number
  onCancel: () => void
  onSaved: () => void
}

let _keySeq = 0
const nextKey = () => `row_${++_keySeq}`

export function EstimateEditor({
  estimateId,
  initialLineItems,
  taxRate,
  onCancel,
  onSaved,
}: EstimateEditorProps) {
  const toast = useToast()
  const queryClient = useQueryClient()
  const [rows, setRows] = useState<EditableLine[]>(() =>
    initialLineItems.map(li => ({ ...li, _key: nextKey() })),
  )
  const [saving, setSaving] = useState(false)

  const totals = useMemo(() => {
    const bucket = (t: string) =>
      rows.filter(r => r.line_type === t).reduce((s, r) => s + (Number(r.total_cost) || 0), 0)
    const labor = bucket('labor')
    const materials = bucket('material')
    const markup = bucket('markup')
    const misc = bucket('misc') + bucket('trip') + bucket('permit')
    const tax = bucket('tax')
    const subtotal = labor + materials + markup + misc
    const grand = subtotal + tax
    return { labor, materials, markup, misc, tax, subtotal, grand }
  }, [rows])

  const updateRow = (key: string, patch: Partial<LineItem>) => {
    setRows(prev =>
      prev.map(r => {
        if (r._key !== key) return r
        const next = { ...r, ...patch }
        if ('quantity' in patch || 'unit_cost' in patch) {
          next.total_cost = Number(((next.quantity || 0) * (next.unit_cost || 0)).toFixed(2))
        }
        return next
      }),
    )
  }

  const addRow = () =>
    setRows(prev => [
      ...prev,
      {
        _key: nextKey(),
        line_type: 'labor',
        description: '',
        quantity: 1,
        unit: 'ea',
        unit_cost: 0,
        total_cost: 0,
      },
    ])

  const removeRow = (key: string) => setRows(prev => prev.filter(r => r._key !== key))

  const handleSave = async () => {
    if (rows.length === 0) {
      toast.error('Add at least one line item before saving')
      return
    }
    setSaving(true)
    try {
      await estimatesApi.update(estimateId, {
        line_items: rows.map(r => ({
          line_type: r.line_type,
          description: r.description,
          quantity: Number(r.quantity) || 0,
          unit: r.unit || 'ea',
          unit_cost: Number(r.unit_cost) || 0,
          total_cost: Number(r.total_cost) || 0,
          supplier: r.supplier ?? null,
          sku: r.sku ?? null,
        })),
      })
      await queryClient.invalidateQueries({ queryKey: ['estimates', estimateId] })
      await queryClient.invalidateQueries({ queryKey: ['estimates'] })
      toast.success('Estimate updated')
      onSaved()
    } catch (err) {
      const msg = err instanceof Error && err.message ? err.message : 'Please try again.'
      toast.error('Could not save', msg)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="card p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-[color:var(--ink)]">Editing line items</h3>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={onCancel}
            disabled={saving}
            className="btn btn-ghost text-xs flex items-center gap-1"
          >
            <X size={13} /> Cancel
          </button>
          <button
            type="button"
            onClick={() => void handleSave()}
            disabled={saving}
            className="btn btn-primary text-xs flex items-center gap-1"
          >
            <Save size={13} /> {saving ? 'Saving…' : 'Save Changes'}
          </button>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead className="text-left text-[color:var(--muted-ink)]">
            <tr>
              <th className="px-2 py-1">Type</th>
              <th className="px-2 py-1">Description</th>
              <th className="px-2 py-1 w-16">Qty</th>
              <th className="px-2 py-1 w-16">Unit</th>
              <th className="px-2 py-1 w-24">Unit Cost</th>
              <th className="px-2 py-1 w-24 text-right">Total</th>
              <th className="px-2 py-1 w-8"></th>
            </tr>
          </thead>
          <tbody>
            {rows.map(r => (
              <tr key={r._key} className="border-t border-[color:var(--line)]">
                <td className="px-2 py-1">
                  <select
                    value={r.line_type}
                    onChange={e => updateRow(r._key, { line_type: e.target.value })}
                    className="input text-xs w-full"
                  >
                    {LINE_TYPES.map(t => (
                      <option key={t} value={t}>{t}</option>
                    ))}
                  </select>
                </td>
                <td className="px-2 py-1">
                  <input
                    type="text"
                    value={r.description}
                    onChange={e => updateRow(r._key, { description: e.target.value })}
                    className="input text-xs w-full"
                  />
                </td>
                <td className="px-2 py-1">
                  <input
                    type="number"
                    step="0.01"
                    value={r.quantity}
                    onChange={e => updateRow(r._key, { quantity: Number(e.target.value) })}
                    className="input text-xs w-full"
                  />
                </td>
                <td className="px-2 py-1">
                  <input
                    type="text"
                    value={r.unit}
                    onChange={e => updateRow(r._key, { unit: e.target.value })}
                    className="input text-xs w-full"
                  />
                </td>
                <td className="px-2 py-1">
                  <input
                    type="number"
                    step="0.01"
                    value={r.unit_cost}
                    onChange={e => updateRow(r._key, { unit_cost: Number(e.target.value) })}
                    className="input text-xs w-full"
                  />
                </td>
                <td className="px-2 py-1 text-right tabular-nums">
                  {formatCurrencyDecimal(r.total_cost ?? 0)}
                </td>
                <td className="px-2 py-1">
                  <button
                    type="button"
                    onClick={() => removeRow(r._key)}
                    disabled={saving}
                    className="text-[color:var(--muted-ink)] hover:text-[color:var(--danger)]"
                    aria-label="Remove line"
                  >
                    <Trash2 size={13} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <button
        type="button"
        onClick={addRow}
        disabled={saving}
        className="btn btn-ghost text-xs flex items-center gap-1"
      >
        <Plus size={13} /> Add line
      </button>

      <div className="rounded-lg border border-[color:var(--line)] p-3 text-xs space-y-1 tabular-nums">
        <div className="flex justify-between"><span>Labor</span><span>{formatCurrencyDecimal(totals.labor)}</span></div>
        <div className="flex justify-between"><span>Materials</span><span>{formatCurrencyDecimal(totals.materials)}</span></div>
        <div className="flex justify-between"><span>Markup</span><span>{formatCurrencyDecimal(totals.markup)}</span></div>
        <div className="flex justify-between"><span>Misc / Trip / Permit</span><span>{formatCurrencyDecimal(totals.misc)}</span></div>
        <div className="flex justify-between border-t border-[color:var(--line)] pt-1">
          <span>Subtotal</span><span>{formatCurrencyDecimal(totals.subtotal)}</span>
        </div>
        <div className="flex justify-between">
          <span>Tax ({(taxRate * 100).toFixed(2)}%)</span>
          <span>{formatCurrencyDecimal(totals.tax)}</span>
        </div>
        <div className="flex justify-between font-semibold text-[color:var(--ink)]">
          <span>Grand total</span><span>{formatCurrencyDecimal(totals.grand)}</span>
        </div>
      </div>
    </div>
  )
}
