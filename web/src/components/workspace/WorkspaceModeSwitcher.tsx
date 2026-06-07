'use client'

import { memo } from 'react'
import { motion } from 'framer-motion'
import { Wrench, FileText, Building2, Check } from 'lucide-react'
import { useReducedMotion } from '@/lib/useReducedMotion'

export type WorkspaceMode = 'repair' | 'blueprint' | 'floorplan'

const MODES = [
  {
    value: 'repair' as WorkspaceMode,
    label: 'Repair Pricing',
    description: 'Fast service pricing for field work.',
    icon: Wrench,
  },
  {
    value: 'blueprint' as WorkspaceMode,
    label: 'Blueprint Pricing',
    description: 'Upload plans and review takeoff assumptions.',
    icon: FileText,
  },
  {
    value: 'floorplan' as WorkspaceMode,
    label: 'Floorplan Pricing',
    description: 'Guide rough-in and finish estimates from plan context.',
    icon: Building2,
  },
] as const

interface WorkspaceModeSwitcherProps {
  mode: WorkspaceMode
  onChange: (mode: WorkspaceMode) => void
}

export const WorkspaceModeSwitcher = memo(function WorkspaceModeSwitcher({
  mode,
  onChange,
}: WorkspaceModeSwitcherProps) {
  const reduce = useReducedMotion()

  return (
    <div className="grid gap-2 sm:grid-cols-3" role="radiogroup" aria-label="Pricing mode">
      {MODES.map((option) => {
        const active = mode === option.value
        const Icon = option.icon

        return (
          <button
            key={option.value}
            role="radio"
            aria-checked={active}
            onClick={() => onChange(option.value)}
            className={`relative flex items-start gap-3 rounded-[1.25rem] border p-4 text-left transition-all duration-fast active:scale-[0.99] ${
              active
                ? 'border-[color:var(--accent)] bg-[color:var(--accent-soft)]'
                : 'border-[color:var(--line)] bg-[color:var(--panel-solid)] hover:bg-[color:var(--panel-strong)] hover:border-[color:var(--line-strong)]'
            }`}
          >
            {active && !reduce && (
              <motion.div
                layoutId="mode-switcher-indicator"
                className="absolute inset-0 rounded-[1.25rem] border-2 border-[color:var(--accent)]"
                transition={{ type: 'spring', damping: 28, stiffness: 320 }}
              />
            )}
            <span
              className={`relative flex size-10 shrink-0 items-center justify-center rounded-[1rem] ${
                active
                  ? 'bg-[color:var(--accent)] text-white'
                  : 'bg-[color:var(--panel-strong)] text-[color:var(--muted-ink)]'
              }`}
            >
              <Icon size={18} aria-hidden="true" />
            </span>
            <span className="relative min-w-0">
              <span className={`block text-sm font-semibold ${active ? 'text-[color:var(--accent-strong)]' : 'text-[color:var(--ink)]'}`}>
                {option.label}
              </span>
              <span className="mt-0.5 block text-xs leading-relaxed text-[color:var(--muted-ink)]">
                {option.description}
              </span>
            </span>
            {active && (
              <span className="relative ml-auto flex size-5 items-center justify-center rounded-full bg-[color:var(--accent)] text-white">
                <Check size={12} strokeWidth={3} aria-hidden="true" />
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
})
