import { memo } from 'react'
import { cn, getConfidenceColor } from '@/lib/utils'
import { CheckCircle2, AlertCircle, XCircle } from 'lucide-react'

interface Props {
  label: string
  score: number
  size?: 'sm' | 'md'
}

export const ConfidenceBadge = memo(function ConfidenceBadge({ label, score, size = 'sm' }: Props) {
  const normalizedLabel = label?.toUpperCase()
  const safeLabel = normalizedLabel === 'HIGH' || normalizedLabel === 'MEDIUM' || normalizedLabel === 'LOW'
    ? normalizedLabel
    : 'HIGH'
  const Icon = safeLabel === 'HIGH' ? CheckCircle2 : safeLabel === 'MEDIUM' ? AlertCircle : XCircle
  const scorePercent = Math.round(Math.max(0, score) * 100)

  return (
    <span className={cn(
      'inline-flex items-center gap-1.5 rounded-full border font-semibold',
      size === 'sm' ? 'px-2 py-0.5 text-[11px]' : 'px-2.5 py-1 text-xs',
      getConfidenceColor(safeLabel)
    )}>
      <Icon className={size === 'sm' ? 'w-3 h-3' : 'w-4 h-4'} />
      {safeLabel} · {scorePercent}%
    </span>
  )
})
