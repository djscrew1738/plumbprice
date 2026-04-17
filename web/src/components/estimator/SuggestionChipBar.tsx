'use client'

import { FileUp } from 'lucide-react'
import type { PricingTemplateSummary } from '@/lib/api'
import type { Suggestion } from './SuggestionGrid'

interface SuggestionChipBarProps {
  suggestions: Suggestion[]
  uploadMode: boolean
  loading: boolean
  pricingTemplates: PricingTemplateSummary[]
  onSendMessage: (text: string) => void
  onTemplateSelect: (id: string) => void
}

export function SuggestionChipBar({
  suggestions,
  uploadMode,
  loading,
  pricingTemplates,
  onSendMessage,
  onTemplateSelect,
}: SuggestionChipBarProps) {
  return (
    <div className="border-b border-[color:var(--line)] bg-[hsl(var(--panel-hsl)/0.95)] backdrop-blur-xl px-3 py-2.5">
      {uploadMode ? (
        <div className="shell-chip">
          <FileUp size={13} />
          Upload workflow coming next.
        </div>
      ) : (
        <div className="flex items-center gap-1.5 overflow-x-auto scrollbar-hide snap-x snap-mandatory">
          {pricingTemplates.length > 0 && (
            <select
              defaultValue=""
              onChange={e => {
                const id = e.target.value
                if (!id) return
                e.target.value = ''
                onTemplateSelect(id)
              }}
              className="shrink-0 rounded-full border border-[color:var(--line)] bg-[color:var(--panel)] px-2 py-1 text-[11px] font-medium text-[color:var(--muted-ink)]"
            >
              <option value="">Templates…</option>
              {pricingTemplates.map(t => (
                <option key={t.id} value={t.id}>
                  {t.name}{t.base_price != null ? ` — $${t.base_price}` : ''}
                </option>
              ))}
            </select>
          )}

          {suggestions.map(suggestion => (
            <button
              key={suggestion.short}
              type="button"
              onClick={() => onSendMessage(suggestion.full)}
              disabled={loading}
              className="shrink-0 snap-start rounded-full border border-[color:var(--line)] bg-[color:var(--panel)] px-3 py-1.5 text-[11px] font-medium text-[color:var(--muted-ink)] transition-colors hover:bg-[color:var(--accent-soft)] hover:text-[color:var(--accent-strong)] disabled:opacity-40"
            >
              {suggestion.short}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
