'use client'

import { useState, useEffect, useCallback } from 'react'
import { LayoutGrid, List } from 'lucide-react'
import { templatesApi, type PricingTemplateSummary } from '@/lib/api'
import { formatCurrency } from '@/lib/utils'
import { cn } from '@/lib/utils'
import { Modal } from '@/components/ui/Modal'
import { SearchInput } from '@/components/ui/SearchInput'
import { Badge } from '@/components/ui/Badge'

interface TemplateBrowserProps {
  open: boolean
  onClose: () => void
  onSelect: (template: PricingTemplateSummary) => void
}

type ViewMode = 'grid' | 'list'

export function TemplateBrowser({ open, onClose, onSelect }: TemplateBrowserProps) {
  const [templates, setTemplates] = useState<PricingTemplateSummary[]>([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(false)
  const [viewMode, setViewMode] = useState<ViewMode>('grid')

  useEffect(() => {
    if (!open) return
    let active = true
    setLoading(true)
    templatesApi.list()
      .then(res => { if (active) setTemplates(res.data) })
      .catch(() => {})
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [open])

  const filtered = search
    ? templates.filter(t =>
        t.name.toLowerCase().includes(search.toLowerCase()) ||
        t.description?.toLowerCase().includes(search.toLowerCase()) ||
        t.tags?.some(tag => tag.toLowerCase().includes(search.toLowerCase()))
      )
    : templates

  const handleSelect = useCallback((template: PricingTemplateSummary) => {
    onSelect(template)
    onClose()
  }, [onSelect, onClose])

  const tagVariant = (tag: string): 'info' | 'success' | 'warning' | 'accent' => {
    const lower = tag.toLowerCase()
    if (lower === 'service' || lower === 'repair') return 'info'
    if (lower === 'construction' || lower === 'install') return 'success'
    if (lower === 'commercial') return 'warning'
    return 'accent'
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Pricing Templates"
      description="Select a pre-built job template to quickly generate an estimate."
      size="lg"
    >
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <SearchInput
            value={search}
            onChange={setSearch}
            placeholder="Search templates…"
            isLoading={loading}
            className="flex-1"
          />
          <div className="flex rounded-lg border border-[color:var(--line)] bg-[color:var(--panel-strong)] p-0.5">
            <button
              type="button"
              onClick={() => setViewMode('grid')}
              className={cn(
                'rounded-md p-1.5 transition-colors',
                viewMode === 'grid'
                  ? 'bg-[color:var(--panel)] text-[color:var(--ink)] shadow-sm'
                  : 'text-[color:var(--muted-ink)] hover:text-[color:var(--ink)]'
              )}
              aria-label="Grid view"
            >
              <LayoutGrid size={14} />
            </button>
            <button
              type="button"
              onClick={() => setViewMode('list')}
              className={cn(
                'rounded-md p-1.5 transition-colors',
                viewMode === 'list'
                  ? 'bg-[color:var(--panel)] text-[color:var(--ink)] shadow-sm'
                  : 'text-[color:var(--muted-ink)] hover:text-[color:var(--ink)]'
              )}
              aria-label="List view"
            >
              <List size={14} />
            </button>
          </div>
        </div>

        {loading && (
          <div className="grid gap-3 sm:grid-cols-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="animate-pulse rounded-xl border border-[color:var(--line)] bg-[color:var(--panel-strong)] p-4">
                <div className="h-4 w-3/4 rounded bg-[color:var(--line)]" />
                <div className="mt-2 h-3 w-full rounded bg-[color:var(--line)]" />
                <div className="mt-3 h-5 w-1/3 rounded bg-[color:var(--line)]" />
              </div>
            ))}
          </div>
        )}

        {!loading && filtered.length === 0 && (
          <div className="py-8 text-center text-sm text-[color:var(--muted-ink)]">
            {search ? 'No templates match your search.' : 'No pricing templates available.'}
          </div>
        )}

        {!loading && filtered.length > 0 && viewMode === 'grid' && (
          <div className="grid gap-3 sm:grid-cols-2">
            {filtered.map(template => (
              <button
                key={template.id}
                type="button"
                onClick={() => handleSelect(template)}
                className="group flex flex-col rounded-xl border border-[color:var(--line)] bg-[color:var(--panel)] p-4 text-left transition-all hover:border-[color:var(--accent)] hover:bg-[color:var(--accent-soft)] hover:shadow-md"
              >
                <div className="text-sm font-semibold text-[color:var(--ink)] group-hover:text-[color:var(--accent-strong)]">
                  {template.name}
                </div>
                {template.description && (
                  <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-[color:var(--muted-ink)]">
                    {template.description}
                  </p>
                )}
                <div className="mt-auto flex items-center justify-between gap-2 pt-3">
                  <div className="flex flex-wrap gap-1">
                    {template.tags?.slice(0, 2).map(tag => (
                      <Badge key={tag} variant={tagVariant(tag)} size="sm">{tag}</Badge>
                    ))}
                    {template.region && (
                      <Badge variant="neutral" size="sm">{template.region}</Badge>
                    )}
                  </div>
                  {template.base_price != null && (
                    <span className="text-sm font-bold text-[color:var(--accent-strong)]">
                      {formatCurrency(template.base_price)}
                    </span>
                  )}
                </div>
              </button>
            ))}
          </div>
        )}

        {!loading && filtered.length > 0 && viewMode === 'list' && (
          <div className="divide-y divide-[color:var(--line)] rounded-xl border border-[color:var(--line)]">
            {filtered.map(template => (
              <button
                key={template.id}
                type="button"
                onClick={() => handleSelect(template)}
                className="group flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-[color:var(--accent-soft)]"
              >
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-semibold text-[color:var(--ink)] group-hover:text-[color:var(--accent-strong)]">
                    {template.name}
                  </div>
                  {template.description && (
                    <p className="mt-0.5 truncate text-xs text-[color:var(--muted-ink)]">
                      {template.description}
                    </p>
                  )}
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  {template.tags?.slice(0, 1).map(tag => (
                    <Badge key={tag} variant={tagVariant(tag)} size="sm">{tag}</Badge>
                  ))}
                  {template.base_price != null && (
                    <span className="text-sm font-bold text-[color:var(--accent-strong)]">
                      {formatCurrency(template.base_price)}
                    </span>
                  )}
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </Modal>
  )
}
