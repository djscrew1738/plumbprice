'use client'

import { useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import { Search, Package, Tag, Factory, ArrowUpDown, AlertCircle } from 'lucide-react'
import { Input } from '@/components/ui/Input'
import { Badge } from '@/components/ui/Badge'
import { DataTable, type Column } from '@/components/ui/DataTable'
import { useAdminCatalog, type AdminCatalogItem } from '@/lib/hooks'
import { cn } from '@/lib/utils'

const SUPPLIERS = ['ferguson', 'moore_supply', 'apex'] as const

const CATEGORIES = [
  'commercial_fixture',
  'smart_plumbing',
  'medical_healthcare',
  'restaurant_kitchen',
  'industrial',
  'outdoor_irrigation',
  'piping_fittings',
] as const

export function CatalogBrowser() {
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('')
  const [supplier, setSupplier] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')

  const { data: items = [], isLoading, error } = useAdminCatalog(
    debouncedSearch || undefined,
    category || undefined,
    supplier || undefined,
  )

  const handleSearch = useCallback((value: string) => {
    setSearch(value)
    // Simple debounce
    const timer = setTimeout(() => setDebouncedSearch(value), 300)
    return () => clearTimeout(timer)
  }, [])

  const columns: Column<AdminCatalogItem>[] = [
    {
      key: 'canonical_item',
      header: 'Item',
      render: (row) => (
        <div className="space-y-0.5">
          <div className="font-mono text-xs text-[color:var(--accent)] truncate max-w-[180px]">
            {row.canonical_item}
          </div>
          <div className="text-sm font-medium text-[color:var(--ink)] truncate max-w-[200px]">
            {row.name}
          </div>
          {row.sku && (
            <div className="text-xs text-[color:var(--muted-ink)]">SKU: {row.sku}</div>
          )}
        </div>
      ),
    },
    {
      key: 'supplier',
      header: 'Supplier',
      width: '100px',
      render: (row) => (
        <Badge variant="neutral" size="sm" className="capitalize">
          {row.supplier.replace('_', ' ')}
        </Badge>
      ),
    },
    {
      key: 'pricing',
      header: 'Pricing',
      width: '120px',
      render: (row) => (
        <div className="space-y-0.5 text-sm">
          <div className="font-semibold text-[color:var(--ink)]">${row.cost.toFixed(2)}</div>
          {row.msrp && (
            <div className="text-xs text-[color:var(--muted-ink)] line-through">${row.msrp.toFixed(2)}</div>
          )}
        </div>
      ),
    },
    {
      key: 'category',
      header: 'Category',
      width: '140px',
      render: (row) => (
        <div className="space-y-1">
          {row.category && (
            <Badge variant="info" size="sm" className="capitalize">
              {row.category.replace('_', ' ')}
            </Badge>
          )}
          {row.sub_category && (
            <div className="text-xs text-[color:var(--muted-ink)] capitalize">{row.sub_category.replace('_', ' ')}</div>
          )}
        </div>
      ),
    },
    {
      key: 'inventory',
      header: 'Stock',
      width: '100px',
      render: (row) => (
        <div className="space-y-0.5">
          <div className="flex items-center gap-1">
            <span className={cn(
              'inline-block h-2 w-2 rounded-full',
              row.in_stock ? 'bg-emerald-500' : 'bg-red-500'
            )} />
            <span className="text-xs text-[color:var(--muted-ink)]">
              {row.in_stock ? 'In Stock' : 'Out'}
            </span>
          </div>
          {row.lead_time && (
            <div className="text-xs text-amber-600 dark:text-amber-400">{row.lead_time}</div>
          )}
        </div>
      ),
    },
    {
      key: 'meta',
      header: 'Meta',
      width: '140px',
      render: (row) => (
        <div className="space-y-1">
          {row.manufacturer && (
            <div className="flex items-center gap-1 text-xs text-[color:var(--muted-ink)]">
              <Factory size={10} />
              {row.manufacturer}
            </div>
          )}
          {row.tags && row.tags.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {row.tags.slice(0, 3).map(tag => (
                <Badge key={tag} variant="neutral" size="sm" className="text-[10px]">{tag}</Badge>
              ))}
            </div>
          )}
          <div className="text-[10px] text-[color:var(--muted-ink)]">
            Conf: {(row.confidence_score * 100).toFixed(0)}%
          </div>
        </div>
      ),
    },
  ]

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[color:var(--muted-ink)]" />
          <Input
            placeholder="Search items, SKUs, manufacturers..."
            value={search}
            onChange={e => handleSearch(e.target.value)}
            className="pl-9"
          />
        </div>

        <select
          value={category}
          onChange={e => setCategory(e.target.value)}
          className="h-10 rounded-lg border border-[color:var(--line)] bg-[color:var(--panel)] px-3 text-sm text-[color:var(--ink)]"
        >
          <option value="">All Categories</option>
          {CATEGORIES.map(c => (
            <option key={c} value={c}>{c.replace('_', ' ')}</option>
          ))}
        </select>

        <select
          value={supplier}
          onChange={e => setSupplier(e.target.value)}
          className="h-10 rounded-lg border border-[color:var(--line)] bg-[color:var(--panel)] px-3 text-sm text-[color:var(--ink)]"
        >
          <option value="">All Suppliers</option>
          {SUPPLIERS.map(s => (
            <option key={s} value={s}>{s.replace('_', ' ')}</option>
          ))}
        </select>
      </div>

      {/* Results */}
      {error && (
        <div className="flex items-center gap-2 rounded-xl border border-red-500/20 bg-red-500/5 px-4 py-3 text-sm text-red-600">
          <AlertCircle size={14} />
          Failed to load catalog
        </div>
      )}

      <div className="text-xs text-[color:var(--muted-ink)]">
        {isLoading ? 'Loading...' : `${items.length} items found`}
      </div>

      <DataTable
        columns={columns}
        data={items}
        keyExtractor={(row) => `${row.id}`}
        loading={isLoading}
        emptyMessage="No items match your filters"
        className="max-h-[600px] overflow-auto"
      />
    </div>
  )
}
