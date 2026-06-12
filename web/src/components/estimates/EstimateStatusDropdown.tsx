'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDown, Check } from 'lucide-react'
import { cn } from '@/lib/utils'
import { badgeVariants } from '@/components/ui/Badge'
import { useToast } from '@/components/ui/Toast'
import { api } from '@/lib/api'
import { ESTIMATE_STATUS_VARIANT } from '@/lib/badgeConfig'

export const STATUS_OPTIONS = [
  { value: 'draft',    label: 'Draft'    },
  { value: 'sent',     label: 'Sent'     },
  { value: 'accepted', label: 'Accepted' },
  { value: 'rejected', label: 'Rejected' },
] as const

interface EstimateStatusDropdownProps {
  estimateId: number
  current: string
  onChange: (id: number, status: string) => void
}

export function EstimateStatusDropdown({ estimateId, current, onChange }: EstimateStatusDropdownProps) {
  const [open, setOpen] = useState(false)
  const [updating, setUpdating] = useState(false)
  const toast = useToast()

  const handleSelect = async (status: string) => {
    if (status === current) { setOpen(false); return }
    setUpdating(true)
    setOpen(false)
    try {
      await api.patch(`/estimates/${estimateId}/status`, { status })
      onChange(estimateId, status)
    } catch {
      toast.error('Could not update status', 'Please try again.')
    } finally {
      setUpdating(false)
    }
  }

  return (
    <div className="relative">
      <button
        onClick={(e) => { e.stopPropagation(); setOpen(o => !o) }}
        disabled={updating}
        className={cn(
          badgeVariants({ variant: ESTIMATE_STATUS_VARIANT[current] ?? 'neutral', size: 'sm' }),
          'cursor-pointer gap-1 transition-opacity hover:opacity-80',
          updating && 'pointer-events-none opacity-50',
        )}
      >
        {current}
        <ChevronDown size={9} className={cn('transition-transform', open && 'rotate-180')} />
      </button>
      <AnimatePresence>
        {open && (
          <>
            <div className="fixed inset-0 z-10" onClick={(e) => { e.stopPropagation(); setOpen(false) }} aria-hidden="true" />
            <motion.div
              initial={{ opacity: 0, y: -4, scale: 0.96 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -4, scale: 0.96 }}
              transition={{ duration: 0.1 }}
              className="absolute left-0 top-full z-20 mt-1 min-w-[110px] overflow-hidden rounded-xl border border-[color:var(--line)] bg-[color:var(--panel)] shadow-2xl"
            >
              {STATUS_OPTIONS.map(opt => (
                <button
                  key={opt.value}
                  onClick={(e) => { e.stopPropagation(); handleSelect(opt.value) }}
                  className={cn(
                    'flex w-full items-center justify-between px-3 py-2 text-left text-xs font-medium transition-colors',
                    opt.value === current
                      ? 'bg-[color:var(--accent-soft)] text-[color:var(--accent-strong)]'
                      : 'text-[color:var(--muted-ink)] hover:bg-[color:var(--panel-strong)] hover:text-[color:var(--ink)]',
                  )}
                >
                  {opt.label}
                  {opt.value === current && <Check size={10} />}
                </button>
              ))}
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  )
}
