'use client'

import { useMemo } from 'react'
import { Pencil, Save, RefreshCw, Plus } from 'lucide-react'
import { type CanonicalItem, type CanonicalItemSupplier } from '@/lib/api'
import { DataTable, type Column } from '@/components/ui/DataTable'
import { SearchInput } from '@/components/ui/SearchInput'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { Modal } from '@/components/ui/Modal'
import { Skeleton } from '@/components/ui/Skeleton'
import { Tooltip } from '@/components/ui/Tooltip'

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
  // Add new item
  addItemOpen: boolean
  addItemName: string
  addItemValues: EditValues
  addItemSaving: boolean
  onOpenAddItem: () => void
  onCloseAddItem: () => void
  onAddItemNameChange: (value: string) => void
  onAddItemValueChange: (slug: SupplierSlug, field: string, value: string | number) => void
  onSaveAddItem: () => void
}

function SupplierPriceFields({
  slug,
  values,
  onChange,
}: {
  slug: SupplierSlug
  values: Partial<CanonicalItemSupplier>
  onChange: (slug: SupplierSlug, field: string, value: string | number) => void
}) {
  return (
    <div className="rounded-xl border border-[color:var(--line)] p-4 space-y-3">
      <p className="text-xs font-bold uppercase tracking-wider text-[color:var(--muted-ink)]">{slug.replace('_', ' ')}</p>
      <div className="grid grid-cols-2 gap-3">
        <Input
          label="Name"
          size="sm"
          type="text"
          value={values?.name ?? ''}
          onChange={e => onChange(slug, 'name', e.target.value)}
          placeholder="Product name"
        />
        <Input
          label="SKU"
          size="sm"
          type="text"
          value={values?.sku ?? ''}
          onChange={e => onChange(slug, 'sku', e.target.value)}
          placeholder="Optional"
          className="font-mono"
        />
        <Input
          label="Cost ($)"
          size="sm"
          type="number"
          min={0}
          step={0.01}
          value={values?.cost ?? ''}
          onChange={e => onChange(slug, 'cost', parseFloat(e.target.value) || 0)}
          className="tabular-nums"
        />
        <Select
          label="Unit"
          size="sm"
          options={UNIT_OPTIONS}
          value={values?.unit ?? 'ea'}
          onChange={val => onChange(slug, 'unit', val)}
        />
      </div>
    </div>
  )
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
  addItemOpen,
  addItemName,
  addItemValues,
  addItemSaving,
  onOpenAddItem,
  onCloseAddItem,
  onAddItemNameChange,
  onAddItemValueChange,
  onSaveAddItem,
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
        <Tooltip content="Edit prices">
          <button
            onClick={(e) => { e.stopPropagation(); onOpenEditItem(item) }}
            className="flex min-h-[32px] min-w-[32px] items-center justify-center rounded-lg p-2 text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] hover:bg-[color:var(--panel-strong)] transition-colors"
            aria-label={`Edit prices for ${item.canonical_item}`}
          >
            <Pencil size={12} />
          </button>
        </Tooltip>
      ),
    },
  ], [onOpenEditItem])

  if (loading) {
    return <Skeleton variant="card" count={6} className="h-12 rounded-xl" />
  }

  return (
    <>
      <div className="flex items-center gap-2 mb-3">
        <SearchInput
          value={priceSearch}
          onChange={onPriceSearchChange}
          placeholder="Search canonical items…"
          aria-label="Search canonical items"
          className="flex-1"
        />
        <button
          onClick={onOpenAddItem}
          className="btn-primary shrink-0 px-3 py-2 min-h-[40px] flex items-center gap-1.5 text-sm"
          aria-label="Add new canonical item"
        >
          <Plus size={14} />
          <span className="hidden sm:inline">Add Item</span>
        </button>
      </div>

      <DataTable
        columns={columns}
        data={filteredItems}
        keyExtractor={(item) => item.canonical_item}
        stickyHeader
        emptyMessage="No items found. Prices are seeded from the supplier catalog on first run."
        className="max-h-[65vh]"
      />

      {/* Edit existing item modal */}
      <Modal
        open={editItem !== null}
        onClose={onCloseEditItem}
        title="Edit Item Prices"
        description={editItem?.canonical_item}
        size="md"
      >
        <div className="space-y-5">
          {SUPPLIERS.map(slug => (
            <SupplierPriceFields key={slug} slug={slug} values={editValues[slug]} onChange={onEditValueChange} />
          ))}
        </div>
        <div className="mt-4 flex justify-end gap-2">
          <button onClick={onCloseEditItem} className="rounded-xl border border-[color:var(--line)] px-4 py-2 text-sm font-medium text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] transition-colors">
            Cancel
          </button>
          <button
            onClick={onSaveEditItem}
            disabled={editSaving}
            className="btn-primary rounded-xl px-4 py-2 text-sm disabled:opacity-40 flex items-center gap-1.5"
            aria-busy={editSaving}
          >
            {editSaving ? <RefreshCw size={13} className="animate-spin" /> : <Save size={13} />}
            Save
          </button>
        </div>
      </Modal>

      {/* Add new canonical item modal */}
      <Modal
        open={addItemOpen}
        onClose={onCloseAddItem}
        title="Add New Item"
        description="Create a new canonical item with prices for one or more suppliers."
        size="md"
      >
        <div className="space-y-5">
          <Input
            label="Canonical Item Key"
            placeholder="e.g. 1_2_inch_copper_elbow"
            value={addItemName}
            onChange={e => onAddItemNameChange(e.target.value)}
            helperText="Unique identifier used internally (lowercase, underscores). Must be at least 3 characters."
          />
          <p className="text-xs text-[color:var(--muted-ink)]">Enter prices for at least one supplier below.</p>
          {SUPPLIERS.map(slug => (
            <SupplierPriceFields key={slug} slug={slug} values={addItemValues[slug] ?? {}} onChange={onAddItemValueChange} />
          ))}
        </div>
        <div className="mt-4 flex justify-end gap-2">
          <button onClick={onCloseAddItem} className="rounded-xl border border-[color:var(--line)] px-4 py-2 text-sm font-medium text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] transition-colors">
            Cancel
          </button>
          <button
            onClick={onSaveAddItem}
            disabled={addItemSaving || addItemName.trim().length < 3}
            className="btn-primary rounded-xl px-4 py-2 text-sm disabled:opacity-40 flex items-center gap-1.5"
            aria-busy={addItemSaving}
          >
            {addItemSaving ? <RefreshCw size={13} className="animate-spin" /> : <Plus size={13} />}
            Add Item
          </button>
        </div>
      </Modal>
    </>
  )
}
