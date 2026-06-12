'use client'

import { useState, useEffect } from 'react'
import { Smartphone } from 'lucide-react'
import { cn } from '@/lib/utils'
import { haptic } from '@/lib/haptics'

export function FieldModeToggle() {
  const [enabled, setEnabled] = useState(() => {
    try { return localStorage.getItem('v3_field_mode') === 'true' } catch { return false }
  })

  useEffect(() => {
    document.documentElement.classList.toggle('field-mode', enabled)
    try { localStorage.setItem('v3_field_mode', String(enabled)) } catch { /* noop */ }
  }, [enabled])

  return (
    <button
      type="button"
      onClick={() => { haptic('tap'); setEnabled(v => !v) }}
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-[10px] font-medium transition-colors',
        enabled
          ? 'border-amber-400 bg-amber-100 text-amber-700'
          : 'border-[color:var(--line)] bg-[color:var(--panel-strong)] text-[color:var(--muted-ink)] hover:bg-[color:var(--accent-soft)] hover:text-[color:var(--accent-strong)]'
      )}
      title={enabled ? 'Field mode on — large touch targets' : 'Toggle field mode'}
    >
      <Smartphone size={10} />
      {enabled ? 'Field' : 'Field mode'}
    </button>
  )
}
