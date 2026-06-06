'use client'

import { motion } from 'framer-motion'
import { Wrench, XCircle } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ToolCallBubbleProps {
  tool: string
  latencyMs?: number
  error?: string | null
}

const TOOL_LABELS: Record<string, string> = {
  search_materials: 'Searching supplier catalog',
  get_labor_template: 'Loading labor rates',
  lookup_permit_cost: 'Checking permit fees',
  check_price_history: 'Analyzing price trends',
  get_market_adjustments: 'Checking market conditions',
}

export function ToolCallBubble({ tool, latencyMs, error }: ToolCallBubbleProps) {
  const label = TOOL_LABELS[tool] || tool
  const hasError = !!error

  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      className={cn(
        'flex items-center gap-2 rounded-lg border px-3 py-2 text-xs',
        hasError
          ? 'border-red-200 bg-red-50 text-red-700'
          : 'border-[color:var(--line)] bg-[color:var(--panel-strong)] text-[color:var(--muted-ink)]'
      )}
    >
      {hasError ? (
        <XCircle size={14} className="text-red-500 shrink-0" />
      ) : (
        <Wrench size={14} className="text-[color:var(--accent)] shrink-0" />
      )}
      <span className="font-medium">{label}</span>
      {!hasError && latencyMs !== undefined && (
        <span className="ml-auto text-[10px] opacity-60">{latencyMs}ms</span>
      )}
      {hasError && (
        <span className="ml-auto text-[10px] text-red-500">Failed</span>
      )}
    </motion.div>
  )
}
