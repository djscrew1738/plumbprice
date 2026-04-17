'use client'

import { motion } from 'framer-motion'
import { Save, RefreshCw } from 'lucide-react'
import { Badge } from '@/components/ui/Badge'
import { Input } from '@/components/ui/Input'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { Skeleton } from '@/components/ui/Skeleton'

interface MarkupRule { job_type: string; materials_markup_pct: number; misc_disposal_flat: number }

const CAT_VARIANT: Record<string, 'success' | 'warning' | 'info' | 'accent' | 'neutral'> = {
  service: 'info',
  construction: 'warning',
  commercial: 'accent',
}

export interface MarkupRulesTabProps {
  markupRules: MarkupRule[]
  loading: boolean
  saving: boolean
  saveOk: boolean
  confirmSave: boolean
  onUpdateMarkup: (jobType: string, field: keyof MarkupRule, value: number) => void
  onSetConfirmSave: (open: boolean) => void
  onSaveMarkup: () => void
}

export function MarkupRulesTab({
  markupRules,
  loading,
  saving,
  saveOk,
  confirmSave,
  onUpdateMarkup,
  onSetConfirmSave,
  onSaveMarkup,
}: MarkupRulesTabProps) {
  if (loading) {
    return <Skeleton variant="card" count={3} className="h-32 rounded-2xl" />
  }

  return (
    <div className="space-y-3">
      {saveOk && (
        <div className="flex items-center gap-2 rounded-xl border border-[hsl(var(--success)/0.2)] bg-[hsl(var(--success)/0.1)] px-4 py-3 text-sm text-[hsl(var(--success))]">
          Markup rules saved successfully
        </div>
      )}
      {markupRules.map((rule, i) => (
        <motion.div
          key={rule.job_type}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.18, delay: i * 0.05 }}
          className="card p-5 hover:shadow-lg transition-all"
        >
          <div className="mb-4 flex items-center gap-2">
            <Badge variant={CAT_VARIANT[rule.job_type] ?? 'neutral'}>
              {rule.job_type}
            </Badge>
            <span className="text-sm font-semibold capitalize text-[color:var(--ink)]">{rule.job_type} Jobs</span>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input
              id={`${rule.job_type}-markup-pct`}
              label="Materials Markup"
              type="number"
              size="md"
              value={rule.materials_markup_pct}
              onChange={e => onUpdateMarkup(rule.job_type, 'materials_markup_pct', parseFloat(e.target.value))}
              step={1} min={0} max={200}
              rightIcon={<span className="text-xs font-bold text-[color:var(--muted-ink)]">%</span>}
            />
            <Input
              id={`${rule.job_type}-misc-flat`}
              label="Misc / Disposal Flat"
              type="number"
              size="md"
              value={rule.misc_disposal_flat}
              onChange={e => onUpdateMarkup(rule.job_type, 'misc_disposal_flat', parseFloat(e.target.value))}
              step={5} min={0}
              leftIcon={<span className="text-xs font-bold text-[color:var(--muted-ink)]">$</span>}
            />
          </div>
        </motion.div>
      ))}
      {markupRules.length > 0 && (
        <motion.div className="flex items-center gap-2">
          <ConfirmDialog
            open={confirmSave}
            onClose={() => onSetConfirmSave(false)}
            onConfirm={onSaveMarkup}
            title="Save Markup Rules"
            description="Save changes to all markup rules?"
            confirmLabel={saving ? 'Saving…' : 'Confirm Save'}
            isLoading={saving}
          />
          <motion.button
            onClick={() => onSetConfirmSave(true)}
            whileTap={{ scale: 0.97 }}
            className="btn-primary w-full"
          >
            <Save size={15} />
            Save Markup Rules
          </motion.button>
        </motion.div>
      )}
    </div>
  )
}
