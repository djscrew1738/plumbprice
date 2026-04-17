'use client'

import { useMemo } from 'react'
import { Pencil, Save, RefreshCw } from 'lucide-react'
import { type CanonicalItem, type CanonicalItemSupplier } from '@/lib/api'
import { DataTable, type Column } from '@/components/ui/DataTable'
import { SearchInput } from '@/components/ui/SearchInput'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { Modal } from '@/components/ui/Modal'
import { Skeleton } from '@/components/ui/Skeleton'

const SUPPLIERS = ['ferguson', 'moore_supply', 'apex'] as const
type SupplierSlug = typeof SUPPLIERS[number]

type EditValues = Record<SupplierSlug, Partial<CanonicalItemSupplier>>

const UNIT_OPTIONS = ['ea', 'ft', 'lb', 'gal', 'box', 'pair', 'set'].map(u => ({ value: u, label: u }))

export interface ItemPricesTabProps {
  canonicalItems: CanonicalItem[]
  loading: boolean
  priceSearch: string
  onPriceSearchChange: (value: string) => void
  editItem: CanonicalItem | null
  editValues: EditValues
  editSaving: boolean
  onOpenEditItem: (item: CanonicalItem) => void
  onCloseEditItem: () => void
  onEditValueChange: (slug: SupplierSlug, field: string, value: string | number) => void
  onSaveEditItem: () => void
}

export function ItemPricesTab({
  canonicalItems,
  loading,
  priceSearch,
  onPriceSearchChange,
  editItem,
  editValues,
  editSaving,
  onOpenEditItem,
  onCloseEditItem,
  onEditValueChange,
  onSaveEditItem,
}: ItemPricesTabProps) {
  const filteredItems = useMemo(
    () => canonicalItems
      .filter(item => !priceSearch || item.canonical_item.toLowerCase().includes(priceSearch.toLowerCase()))
      .slice(0, 200),
    [canonicalItems, priceSearch],
  )

  const columns = useMemo<Column<CanonicalItem>[]>(() => [
    {
      key: 'canonical_item',
      header: 'Item',
      render: (item) => (
        <span className="font-mono text-[11px] text-[color:var(--muted-ink)] max-w-[180px] truncate block">
          {item.canonical_item}
        </span>
      ),
    },
    ...SUPPLIERS.map((slug): Column<CanonicalItem> => ({
      key: slug,
      header: slug.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase()),
      render: (item) => {
        const s = item.suppliers[slug]
        return s
          ? <span className="tabular-nums text-[color:var(--ink)] text-xs">${s.cost.toFixed(2)}</span>
          : <span className="text-[color:var(--muted-ink)]">—</span>
      },
    })),
    {
      key: 'actions',
      header: '',
      render: (item) => (
        <button
          onClick={(e) => { e.stopPropagation(); onOpenEditItem(item) }}
          className="flex min-h-[32px] min-w-[32px] items-center justify-center rounded-lg p-2 text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] hover:bg-[color:var(--panel-strong)] transition-colors"
          title="Edit prices"
          aria-label={`Edit prices for ${item.canonical_item}`}
        >
          <Pencil size={12} />
        </button>
      ),
    },
  ], [onOpenEditItem])

  if (loading) {
    return <Skeleton variant="card" count={6} className="h-12 rounded-xl" />
  }

  return (
    <>
      <SearchInput
        value={priceSearch}
        onChange={onPriceSearchChange}
        placeholder="Search canonical items…"
        aria-label="Search canonical items"
        className="mb-3"
      />

      <DataTable
        columns={columns}
        data={filteredItems}
        keyExtractor={(item) => item.canonical_item}
        stickyHeader
        emptyMessage="No items found. Prices are seeded from the supplier catalog on first run."
        className="max-h-[65vh]"
      />

      {/* Edit modal */}
      <Modal
        open={editItem !== null}
        onClose={onCloseEditItem}
        title="Edit Item Prices"
        description={editItem?.canonical_item}
        size="md"
      >
        <div className="space-y-5">
          {SUPPLIERS.map(slug => (
            <div key={slug} className="rounded-xl border border-[color:var(--line)] p-4 space-y-3">
              <p className="text-xs font-bold uppercase tracking-wider text-[color:var(--muted-ink)]">{slug.replace('_', ' ')}</p>
              <div className="grid grid-cols-2 gap-3">
                <Input
                  label="Name"
                  size="sm"
                  type="text"
                  value={editValues[slug]?.name ?? ''}
                  onChange={e => onEditValueChange(slug, 'name', e.target.value)}
                  placeholder="Product name"
                />
                <Input
                  label="SKU"
                  size="sm"
                  type="text"
                  value={editValues[slug]?.sku ?? ''}
                  onChange={e => onEditValueChange(slug, 'sku', e.target.value)}
                  placeholder="Optional"
                  className="font-mono"
                />
                <Input
                  label="Cost ($)"
                  size="sm"
                  type="number"
                  min={0}
                  step={0.01}
                  value={editValues[slug]?.cost ?? ''}
                  onChange={e => onEditValueChange(slug, 'cost', parseFloat(e.target.value) || 0)}
                  className="tabular-nums"
                />
                <Select
                  label="Unit"
                  size="sm"
                  options={UNIT_OPTIONS}
                  value={editValues[slug]?.unit ?? 'ea'}
                  onChange={val => onEditValueChange(slug, 'unit', val)}
                />
              </div>
            </div>
          ))}
        </div>
        <div className="mt-4 flex justify-end gap-2">
          <button onClick={onCloseEditItem} className="rounded-xl border border-[color:var(--line)] px-4 py-2 text-sm font-medium text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] transition-colors">
            Cancel
          </button>
          <button
            onClick={onSaveEditItem}
            disabled={editSaving}
            className="btn-primary rounded-xl px-4 py-2 text-sm disabled:opacity-40"
          >
            {editSaving ? <RefreshCw size={13} className="animate-spin" /> : <Save size={13} />}
            Save
          </button>
        </div>
      </Modal>
    </>
  )
}
