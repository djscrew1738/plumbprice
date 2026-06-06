'use client'

import { useState, useEffect } from 'react'
import { marketPricingApiV3, type MarketAdjustment } from '@/lib/api-v3'
import { formatDateMedium } from '@/lib/formatters'
import { TrendingUp, TrendingDown, Plus, Trash2, AlertCircle } from 'lucide-react'
import { cn } from '@/lib/utils'

export default function MarketPricingAdminPage() {
  const [adjustments, setAdjustments] = useState<MarketAdjustment[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [preview, setPreview] = useState<{ base_total: number; adjusted_total: number; overall_factor: number; adjustments: Array<{ name: string; category: string; factor: number }> } | null>(null)

  useEffect(() => {
    loadAdjustments()
  }, [])

  async function loadAdjustments() {
    try {
      setLoading(true)
      const res = await marketPricingApiV3.listAdjustments()
      setAdjustments(res.data)
    } catch {
      setError('Failed to load adjustments')
    } finally {
      setLoading(false)
    }
  }

  async function handlePreview() {
    try {
      const res = await marketPricingApiV3.preview({
        county: 'Dallas',
        base_labor: 500,
        base_materials: 800,
        base_markup: 200,
        base_misc: 50,
        base_trip: 115,
        tax_rate: 0.0825,
      })
      setPreview(res.data)
    } catch {
      setError('Preview failed')
    }
  }

  async function handleToggle(id: number, current: boolean) {
    // Soft delete = mark inactive
    if (current) {
      await marketPricingApiV3.deleteAdjustment(id)
      loadAdjustments()
    }
  }

  return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-[color:var(--ink)]">Market Pricing</h1>
          <p className="text-sm text-[color:var(--muted-ink)] mt-1">
            Dynamic pricing adjustments applied to estimates based on market conditions.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handlePreview}
            className="rounded-lg border border-[color:var(--line)] bg-[color:var(--panel-strong)] px-4 py-2 text-sm font-medium text-[color:var(--ink)] hover:bg-[color:var(--panel)]"
          >
            Preview Impact
          </button>
          <button className="rounded-lg bg-[color:var(--accent)] px-4 py-2 text-sm font-semibold text-white hover:opacity-90 inline-flex items-center gap-1.5">
            <Plus size={16} />
            New Adjustment
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 flex items-center gap-2">
          <AlertCircle size={16} />
          {error}
        </div>
      )}

      {preview && (
        <div className="mb-6 rounded-xl border border-[color:var(--line)] bg-[color:var(--panel-strong)] p-5">
          <h3 className="text-sm font-semibold text-[color:var(--ink)] mb-3">Impact Preview (Sample Estimate)</h3>
          <div className="grid grid-cols-3 gap-4 mb-3">
            <div>
              <div className="text-[10px] uppercase tracking-wider text-[color:var(--muted-ink)]">Base Total</div>
              <div className="text-lg font-bold text-[color:var(--ink)]">${preview.base_total.toFixed(2)}</div>
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-wider text-[color:var(--muted-ink)]">Adjusted Total</div>
              <div className="text-lg font-bold text-[color:var(--accent-strong)]">${preview.adjusted_total.toFixed(2)}</div>
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-wider text-[color:var(--muted-ink)]">Factor</div>
              <div className="text-lg font-bold text-[color:var(--ink)]">×{preview.overall_factor.toFixed(4)}</div>
            </div>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {preview.adjustments.map(a => (
              <span key={a.name} className={cn(
                'inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-medium',
                a.factor > 1 ? 'bg-amber-50 text-amber-700 border border-amber-200' : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
              )}>
                {a.factor > 1 ? <TrendingUp size={10} /> : <TrendingDown size={10} />}
                {a.name} ({Math.round((a.factor - 1) * 1000) / 10}%)
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="rounded-xl border border-[color:var(--line)] bg-[color:var(--panel)] overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-[color:var(--panel-strong)] border-b border-[color:var(--line)]">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold text-[color:var(--muted-ink)]">Name</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-[color:var(--muted-ink)]">Category</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-[color:var(--muted-ink)]">Factor</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-[color:var(--muted-ink)]">Applies To</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-[color:var(--muted-ink)]">Effective</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-[color:var(--muted-ink)]">Status</th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-[color:var(--muted-ink)]">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[color:var(--line)]">
            {loading ? (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-[color:var(--muted-ink)]">Loading...</td></tr>
            ) : adjustments.length === 0 ? (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-[color:var(--muted-ink)]">No adjustments configured.</td></tr>
            ) : (
              adjustments.map(adj => (
                <tr key={adj.id} className="hover:bg-[color:var(--panel-strong)]/50">
                  <td className="px-4 py-3 font-medium text-[color:var(--ink)]">{adj.name}</td>
                  <td className="px-4 py-3">
                    <span className={cn(
                      'rounded-full px-2 py-0.5 text-[10px] font-medium',
                      adj.category === 'commodity' && 'bg-amber-50 text-amber-700',
                      adj.category === 'seasonal' && 'bg-blue-50 text-blue-700',
                      adj.category === 'demand' && 'bg-purple-50 text-purple-700',
                      adj.category === 'fuel' && 'bg-orange-50 text-orange-700',
                    )}>
                      {adj.category}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={cn('font-semibold', adj.factor > 1 ? 'text-amber-700' : 'text-emerald-700')}>
                      ×{adj.factor.toFixed(3)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-[color:var(--muted-ink)]">{adj.applies_to.join(', ')}</td>
                  <td className="px-4 py-3 text-[color:var(--muted-ink)] text-xs">
                    {formatDateMedium(adj.effective_from)} — {formatDateMedium(adj.effective_until)}
                  </td>
                  <td className="px-4 py-3">
                    <span className={cn(
                      'rounded-full px-2 py-0.5 text-[10px] font-medium',
                      adj.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-zinc-100 text-zinc-500'
                    )}>
                      {adj.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => handleToggle(adj.id, adj.is_active)}
                      className="rounded p-1 text-red-500 hover:bg-red-50"
                      title="Deactivate"
                    >
                      <Trash2 size={14} />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
