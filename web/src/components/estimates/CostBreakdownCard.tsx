'use client'

import { motion } from 'framer-motion'
import {
  TrendingUp, Layers, Tag, CircleDollarSign,
  Calendar, MapPin, FileText,
} from 'lucide-react'
import { Badge } from '@/components/ui/Badge'
import { cn, formatCurrency } from '@/lib/utils'
import { format, isValid } from 'date-fns'

export interface CostBreakdownCardProps {
  laborTotal: number
  materialsTotal: number
  markupTotal: number
  taxTotal: number
  county: string
  taxRate: number
  preferredSupplier?: string | null
  confidenceLabel: string
  confidenceScore: number
  createdAt: string
}

function formatDate(dateStr: string) {
  const d = new Date(dateStr)
  return isValid(d) ? format(d, 'MMMM d, yyyy · h:mm a') : '—'
}

export function CostBreakdownCard({
  laborTotal,
  materialsTotal,
  markupTotal,
  taxTotal,
  county,
  taxRate,
  preferredSupplier,
  confidenceLabel,
  confidenceScore,
  createdAt,
}: CostBreakdownCardProps) {
  const costCards = [
    { label: 'Labor',     value: laborTotal,     icon: TrendingUp,       bg: 'bg-[hsl(var(--info)/0.1)] border-[hsl(var(--info)/0.2)]'     },
    { label: 'Materials', value: materialsTotal,  icon: Layers,           bg: 'bg-[hsl(var(--success)/0.1)] border-[hsl(var(--success)/0.2)]'},
    { label: 'Markup',    value: markupTotal,     icon: Tag,              bg: 'bg-[hsl(var(--warning)/0.1)] border-[hsl(var(--warning)/0.2)]'   },
    { label: 'Tax',       value: taxTotal,        icon: CircleDollarSign, bg: 'bg-white/[0.03] border-white/[0.08]'   },
  ]

  return (
    <>
      {/* Summary cards */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2 }}
        className="grid grid-cols-2 md:grid-cols-4 gap-3"
      >
        {costCards.map(({ label, value, icon: Icon, bg }) => (
          <div key={label} className="card p-3.5 flex items-center gap-3">
            <div className={cn('w-8 h-8 rounded-xl flex items-center justify-center border shrink-0', bg)}>
              <Icon size={13} className="text-[color:var(--accent)]" />
            </div>
            <div className="min-w-0">
              <div className="text-[10px] text-[color:var(--muted-ink)] font-bold uppercase tracking-wider">{label}</div>
              <div className="text-sm font-bold text-[color:var(--ink)] tabular-nums">{formatCurrency(value)}</div>
            </div>
          </div>
        ))}
      </motion.div>

      {/* Metadata row */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2, delay: 0.05 }}
        className="card p-4 flex flex-wrap gap-4 text-sm"
      >
        <div className="flex items-center gap-2 text-[color:var(--muted-ink)]">
          <Calendar size={13} className="text-[color:var(--muted-ink)] shrink-0" />
          <span className="text-xs">{formatDate(createdAt)}</span>
        </div>
        <div className="flex items-center gap-2 text-[color:var(--muted-ink)]">
          <MapPin size={13} className="text-[color:var(--muted-ink)] shrink-0" />
          <span className="text-xs">{county} County · {(taxRate * 100).toFixed(2)}% tax</span>
        </div>
        {preferredSupplier && (
          <div className="flex items-center gap-2 text-[color:var(--muted-ink)]">
            <FileText size={13} className="text-[color:var(--muted-ink)] shrink-0" />
            <span className="text-xs">Supplier: {preferredSupplier}</span>
          </div>
        )}
        <div className="ml-auto flex items-center gap-2">
          <Badge variant={confidenceLabel?.toLowerCase() === 'high' ? 'success' : confidenceLabel?.toLowerCase() === 'medium' ? 'warning' : 'danger'} size="sm">
            {confidenceLabel} confidence
          </Badge>
          <span className="text-xs text-[color:var(--muted-ink)] tabular-nums">
            {Math.round(confidenceScore * 100)}%
          </span>
        </div>
      </motion.div>
    </>
  )
}
