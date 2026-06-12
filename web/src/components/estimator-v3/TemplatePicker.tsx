'use client'

import { useState, useEffect, useCallback } from 'react'
import { ChevronDown, Sparkles, Plus, Trash2 } from 'lucide-react'
import { chatApiV3, type PromptTemplateResponse } from '@/lib/api-v3'
import { haptic } from '@/lib/haptics'

interface TemplatePickerProps {
  onSelect: (template: string) => void
  onOpenEditor?: () => void
}

const RECENT_CODES = [
  { code: 'TOILET_REPLACE_STANDARD', label: 'Toilet replacement' },
  { code: 'WATER_HEATER_50G_GAS', label: '50-gal gas water heater' },
  { code: 'KITCHEN_FAUCET_REPLACE', label: 'Kitchen faucet' },
  { code: 'DRAIN_CLEAN_STANDARD', label: 'Drain cleaning' },
  { code: 'ANGLE_STOP_REPLACE', label: 'Angle stop replacement' },
]

export function TemplatePicker({ onSelect, onOpenEditor }: TemplatePickerProps) {
  const [open, setOpen] = useState(false)
  const [templates, setTemplates] = useState<PromptTemplateResponse[]>([])
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await chatApiV3.listTemplates()
      setTemplates(res.data)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (open) load()
  }, [open, load])

  const handleDelete = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      await chatApiV3.deleteTemplate(id)
      setTemplates(prev => prev.filter(t => t.id !== id))
      haptic('tap')
    } catch {
      haptic('error')
    }
  }

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => { haptic('tap'); setOpen(o => !o) }}
        className="flex h-11 items-center gap-1 rounded-2xl border border-[color:var(--line)] bg-[color:var(--panel-strong)] px-3 text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] transition-colors"
        aria-label="Insert template"
        title="Templates"
      >
        <Sparkles size={16} />
        <ChevronDown size={12} />
      </button>

      {open && (
        <>
          <div
            className="fixed inset-0 z-40"
            role="presentation"
            tabIndex={-1}
            onClick={() => setOpen(false)}
            onKeyDown={e => { if (e.key === 'Escape') setOpen(false) }}
          />
          <div className="absolute bottom-full left-0 z-50 mb-2 w-64 rounded-xl border border-[color:var(--line)] bg-[color:var(--panel)] p-2 shadow-xl">
            <div className="mb-1 px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-[color:var(--muted-ink)]">Quick Codes</div>
            <div className="mb-2 flex flex-wrap gap-1 px-1">
              {RECENT_CODES.map(c => (
                <button
                  key={c.code}
                  type="button"
                  onClick={() => { onSelect(c.code); setOpen(false) }}
                  className="rounded-full border border-[color:var(--line)] bg-[color:var(--panel-strong)] px-2 py-1 text-[10px] font-medium text-[color:var(--muted-ink)] hover:bg-[color:var(--accent-soft)] hover:text-[color:var(--accent-strong)] transition-colors"
                >
                  {c.label}
                </button>
              ))}
            </div>

            <div className="mb-1 px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-[color:var(--muted-ink)]">Templates</div>
            <div className="max-h-32 overflow-y-auto">
              {loading && <p className="px-2 py-2 text-[11px] text-[color:var(--muted-ink)]">Loading…</p>}
              {!loading && templates.length === 0 && (
                <p className="px-2 py-2 text-[11px] text-[color:var(--muted-ink)]">No templates yet</p>
              )}
              {templates.map(t => (
                <div
                  key={t.id}
                  className="group flex items-center justify-between rounded-lg px-2 py-1.5 hover:bg-[color:var(--panel-strong)]"
                >
                  <button
                    type="button"
                    className="flex-1 text-left text-[11px] text-[color:var(--ink)]"
                    onClick={() => { onSelect(t.template); setOpen(false) }}
                  >
                    {t.name}
                  </button>
                  <button
                    type="button"
                    onClick={(e) => handleDelete(t.id, e)}
                    className="rounded p-1 text-[color:var(--muted-ink)] opacity-0 group-hover:opacity-100 hover:text-red-600 transition-opacity"
                    aria-label="Delete template"
                  >
                    <Trash2 size={10} />
                  </button>
                </div>
              ))}
            </div>

            {onOpenEditor && (
              <button
                type="button"
                onClick={() => { onOpenEditor(); setOpen(false) }}
                className="mt-1 flex w-full items-center gap-1.5 rounded-lg px-2 py-1.5 text-[11px] font-medium text-[color:var(--accent-strong)] hover:bg-[color:var(--accent-soft)] transition-colors"
              >
                <Plus size={12} />
                Create template
              </button>
            )}
          </div>
        </>
      )}
    </div>
  )
}
