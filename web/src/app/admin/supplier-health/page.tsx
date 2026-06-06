'use client'

import { useState, useEffect } from 'react'
import { supplierApiV3 } from '@/lib/api-v3'
import { Activity, Wifi, WifiOff, Package, Webhook } from 'lucide-react'
import { cn } from '@/lib/utils'

interface SupplierHealth {
  id: number
  name: string
  slug: string
  is_active: boolean
  product_count: number
  active_webhooks: number
  webhook_last_delivery: string | null
}

export default function SupplierHealthAdminPage() {
  const [suppliers, setSuppliers] = useState<SupplierHealth[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    loadHealth()
  }, [])

  async function loadHealth() {
    try {
      setLoading(true)
      const res = await supplierApiV3.health()
      setSuppliers(res.data.suppliers)
    } catch {
      setError('Failed to load supplier health')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold text-[color:var(--ink)] mb-1">Supplier Health</h1>
      <p className="text-sm text-[color:var(--muted-ink)] mb-6">
        Monitor supplier integrations, webhook status, and product catalog coverage.
      </p>

      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="grid gap-4">
        {loading ? (
          <div className="rounded-xl border border-[color:var(--line)] bg-[color:var(--panel)] p-8 text-center text-[color:var(--muted-ink)]">
            Loading supplier health...
          </div>
        ) : suppliers.length === 0 ? (
          <div className="rounded-xl border border-[color:var(--line)] bg-[color:var(--panel)] p-8 text-center text-[color:var(--muted-ink)]">
            No suppliers configured.
          </div>
        ) : (
          suppliers.map(s => (
            <div key={s.id} className="rounded-xl border border-[color:var(--line)] bg-[color:var(--panel)] p-5">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className={cn(
                    'flex size-10 items-center justify-center rounded-xl',
                    s.is_active ? 'bg-emerald-50 text-emerald-600' : 'bg-zinc-100 text-zinc-400'
                  )}>
                    <Activity size={20} />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-[color:var(--ink)]">{s.name}</h3>
                    <p className="text-xs text-[color:var(--muted-ink)]">{s.slug}</p>
                  </div>
                </div>
                <span className={cn(
                  'rounded-full px-2.5 py-1 text-[10px] font-medium',
                  s.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-zinc-100 text-zinc-500'
                )}>
                  {s.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div className="rounded-lg bg-[color:var(--panel-strong)] p-3">
                  <div className="flex items-center gap-1.5 text-[color:var(--muted-ink)] mb-1">
                    <Package size={12} />
                    <span className="text-[10px] uppercase tracking-wider">Products</span>
                  </div>
                  <div className="text-lg font-bold text-[color:var(--ink)]">{s.product_count.toLocaleString()}</div>
                </div>

                <div className="rounded-lg bg-[color:var(--panel-strong)] p-3">
                  <div className="flex items-center gap-1.5 text-[color:var(--muted-ink)] mb-1">
                    <Webhook size={12} />
                    <span className="text-[10px] uppercase tracking-wider">Webhooks</span>
                  </div>
                  <div className="text-lg font-bold text-[color:var(--ink)]">{s.active_webhooks}</div>
                </div>

                <div className="rounded-lg bg-[color:var(--panel-strong)] p-3">
                  <div className="flex items-center gap-1.5 text-[color:var(--muted-ink)] mb-1">
                    {s.webhook_last_delivery ? <Wifi size={12} className="text-emerald-500" /> : <WifiOff size={12} />}
                    <span className="text-[10px] uppercase tracking-wider">Last Delivery</span>
                  </div>
                  <div className="text-sm font-semibold text-[color:var(--ink)]">
                    {s.webhook_last_delivery
                      ? new Date(s.webhook_last_delivery).toLocaleString()
                      : 'Never'}
                  </div>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
