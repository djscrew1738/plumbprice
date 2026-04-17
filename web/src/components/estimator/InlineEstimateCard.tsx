'use client'

import { ConfidenceBadge } from './ConfidenceBadge'

interface InlineEstimateCardProps {
  confidenceLabel: string
  confidenceScore: number
  onViewBreakdown: () => void
}

export function InlineEstimateCard({ confidenceLabel, confidenceScore, onViewBreakdown }: InlineEstimateCardProps) {
  return (
    <div className="mt-3 flex items-center justify-between gap-3 border-t border-[color:var(--line)]/50 pt-3">
      <ConfidenceBadge label={confidenceLabel} score={confidenceScore} size="sm" />
      <button
        type="button"
        onClick={onViewBreakdown}
        className="text-xs font-bold text-[color:var(--accent-strong)] underline-offset-2 transition-colors hover:text-[color:var(--accent)] hover:underline"
      >
        View Full Breakdown
      </button>
    </div>
  )
}
