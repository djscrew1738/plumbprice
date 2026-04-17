'use client'

import { useMemo } from 'react'
import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/Badge'
import { DataTable, type Column } from '@/components/ui/DataTable'
import { Skeleton } from '@/components/ui/Skeleton'

interface LaborTemplate {
  code: string; name: string; category: string; base_hours: number
  lead_rate: number; helper_required: boolean; disposal_hours: number
}

const CAT_VARIANT: Record<string, 'success' | 'warning' | 'info' | 'accent' | 'neutral'> = {
  service: 'info',
  construction: 'warning',
  commercial: 'accent',
}

export interface LaborTemplatesTabProps {
  templates: LaborTemplate[]
  loading: boolean
}

export function LaborTemplatesTab({ templates, loading }: LaborTemplatesTabProps) {
  const columns = useMemo<Column<LaborTemplate>[]>(() => [
    {
      key: 'code',
      header: 'Code',
      render: (t) => <span className="font-mono text-[11px] text-[color:var(--muted-ink)]">{t.code}</span>,
    },
    {
      key: 'name',
      header: 'Name',
      render: (t) => <span className="font-medium text-[color:var(--ink)]">{t.name}</span>,
    },
    {
      key: 'category',
      header: 'Category',
      render: (t) => <Badge variant={CAT_VARIANT[t.category] ?? 'neutral'}>{t.category}</Badge>,
    },
    {
      key: 'base_hours',
      header: 'Base Hrs',
      render: (t) => <span className="tabular-nums text-[color:var(--muted-ink)]">{t.base_hours}h</span>,
    },
    {
      key: 'lead_rate',
      header: 'Lead Rate',
      render: (t) => <span className="tabular-nums text-[color:var(--muted-ink)]">${t.lead_rate}/h</span>,
    },
    {
      key: 'helper_required',
      header: 'Helper',
      render: (t) => (
        <Badge variant={t.helper_required ? 'warning' : 'neutral'}>
          {t.helper_required ? 'Yes' : 'No'}
        </Badge>
      ),
    },
    {
      key: 'disposal_hours',
      header: 'Disposal',
      render: (t) => <span className="tabular-nums text-[color:var(--muted-ink)]">{t.disposal_hours}h</span>,
    },
  ], [])

  if (loading) {
    return <Skeleton variant="card" count={5} className="h-16 rounded-2xl" />
  }

  return (
    <>
      {/* Mobile cards */}
      <div className="space-y-2.5 lg:hidden">
        {templates.map((t, i) => (
          <motion.div
            key={t.code}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.18, delay: i * 0.03 }}
            className="card p-4 hover:shadow-lg transition-all"
          >
            <div className="mb-3 flex items-start justify-between gap-2">
              <div>
                <div className="text-sm font-bold text-[color:var(--ink)]">{t.name}</div>
                <div className="mt-0.5 font-mono text-[10px] text-[color:var(--muted-ink)]">{t.code}</div>
              </div>
              <Badge variant={CAT_VARIANT[t.category] ?? 'neutral'}>{t.category}</Badge>
            </div>
            <div className="grid grid-cols-3 gap-2">
              {[
                { label: 'Base Hrs', value: `${t.base_hours}h` },
                { label: 'Lead Rate', value: `$${t.lead_rate}/h` },
                { label: 'Helper', value: t.helper_required ? 'Yes' : 'No' },
              ].map(({ label, value }) => (
                <div key={label} className={cn('card-inset py-2 text-center')}>
                  <div className="text-[10px] text-[color:var(--muted-ink)]">{label}</div>
                  <div className="mt-0.5 text-xs font-bold text-[color:var(--ink)]">{value}</div>
                </div>
              ))}
            </div>
          </motion.div>
        ))}
      </div>

      {/* Desktop table */}
      <div className="hidden lg:block">
        <DataTable
          columns={columns}
          data={templates}
          keyExtractor={(t) => t.code}
          stickyHeader
          className="max-h-[70vh]"
        />
      </div>
    </>
  )
}
