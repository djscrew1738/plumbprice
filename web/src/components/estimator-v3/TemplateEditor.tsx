'use client'

import { useState } from 'react'
import * as Dialog from '@radix-ui/react-dialog'
import { X, Save } from 'lucide-react'
import { chatApiV3 } from '@/lib/api-v3'
import { haptic } from '@/lib/haptics'

interface TemplateEditorProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSaved?: () => void
}

const VARIABLES = ['{{county}}', '{{customer_name}}', '{{job_type}}', '{{address}}']

export function TemplateEditor({ open, onOpenChange, onSaved }: TemplateEditorProps) {
  const [name, setName] = useState('')
  const [template, setTemplate] = useState('')
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    if (!name.trim() || !template.trim()) return
    setSaving(true)
    try {
      await chatApiV3.createTemplate({ name, template })
      haptic('success')
      setName('')
      setTemplate('')
      onSaved?.()
      onOpenChange(false)
    } catch {
      haptic('error')
    } finally {
      setSaving(false)
    }
  }

  const insertVariable = (v: string) => {
    setTemplate(prev => prev + ' ' + v)
  }

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm" />
        <Dialog.Content className="fixed left-1/2 top-[15%] z-50 w-full max-w-md -translate-x-1/2 rounded-2xl border border-[color:var(--line)] bg-[color:var(--panel)] p-5 shadow-2xl focus:outline-none">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-[color:var(--ink)]">New Template</h2>
            <Dialog.Close asChild>
              <button aria-label="Close" className="rounded-lg p-2 text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] transition-colors">
                <X size={15} />
              </button>
            </Dialog.Close>
          </div>

          <div className="space-y-3">
            <div>
              <span className="mb-1 block text-[11px] font-medium text-[color:var(--muted-ink)]">Name</span>
              <input
                type="text"
                value={name}
                onChange={e => setName(e.target.value)}
                placeholder="e.g. Standard repipe"
                className="input w-full rounded-lg px-3 py-2 text-sm"
              />
            </div>

            <div>
              <span className="mb-1 block text-[11px] font-medium text-[color:var(--muted-ink)]">Template</span>
              <textarea
                value={template}
                onChange={e => setTemplate(e.target.value)}
                placeholder="Describe the job using variables…"
                rows={4}
                className="input w-full resize-none rounded-lg px-3 py-2 text-sm"
              />
            </div>

            <div>
              <span className="mb-1 block text-[11px] font-medium text-[color:var(--muted-ink)]">Variables</span>
              <div className="flex flex-wrap gap-1.5">
                {VARIABLES.map(v => (
                  <button
                    key={v}
                    type="button"
                    onClick={() => insertVariable(v)}
                    className="rounded-full bg-[color:var(--accent-soft)] px-2 py-1 text-[10px] font-medium text-[color:var(--accent-strong)] hover:bg-[color:var(--accent)] hover:text-white transition-colors"
                  >
                    {v}
                  </button>
                ))}
              </div>
            </div>

            <div className="rounded-lg bg-[color:var(--panel-strong)] p-3">
              <span className="mb-1 block text-[10px] font-medium uppercase tracking-wider text-[color:var(--muted-ink)]">Preview</span>
              <p className="text-[11px] text-[color:var(--muted-ink)] whitespace-pre-wrap">
                {template || 'Start typing to see preview…'}
              </p>
            </div>

            <button
              type="button"
              onClick={handleSave}
              disabled={saving || !name.trim() || !template.trim()}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-[color:var(--accent)] px-4 py-2.5 text-sm font-semibold text-white hover:opacity-90 transition-opacity disabled:opacity-40"
            >
              <Save size={14} />
              {saving ? 'Saving…' : 'Save template'}
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
