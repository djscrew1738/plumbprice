import { cn, getConfidenceColor } from '@/lib/utils'
import { CheckCircle2, AlertCircle, XCircle } from 'lucide-react'

interface Props {
  label: string
  score: number
  size?: 'sm' | 'md'
}

export function ConfidenceBadge({ label, score, size = 'sm' }: Props) {
  const Icon = label === 'HIGH' ? CheckCircle2 : label === 'MEDIUM' ? AlertCircle : XCircle
  return (
    <span className={cn(
      'inline-flex items-center gap-1 rounded-full font-medium',
      size === 'sm' ? 'text-xs px-2 py-0.5' : 'text-sm px-3 py-1',
      getConfidenceColor(label)
    )}>
      <Icon className={size === 'sm' ? 'w-3 h-3' : 'w-4 h-4'} />
      {label} . {Math.round(score * 100)}%
    </span>
  )
}
