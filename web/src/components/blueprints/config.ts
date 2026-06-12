import { Clock, Loader2, CheckCircle2, AlertCircle } from 'lucide-react'
import type { JobStatus } from '@/lib/hooks'

export const STATUS: Record<
  JobStatus,
  {
    icon: typeof CheckCircle2
    variant: 'neutral' | 'warning' | 'success' | 'danger'
    label: string
  }
> = {
  queued: { icon: Clock, variant: 'neutral', label: 'Queued' },
  processing: { icon: Loader2, variant: 'warning', label: 'Processing' },
  completed: { icon: CheckCircle2, variant: 'success', label: 'Complete' },
  failed: { icon: AlertCircle, variant: 'danger', label: 'Failed' },
}
