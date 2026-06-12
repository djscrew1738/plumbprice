'use client'

import { useState, useCallback } from 'react'
import { estimatesApi } from '@/lib/api/estimates'
import type { ChatPriceResponseV3 } from '@/lib/api-v3'
import type { ChatMessageV3 } from '../ChatMessageListV3'

export interface UseEstimateActionsOptions {
  onMessagesChange?: (updater: (prev: ChatMessageV3[]) => ChatMessageV3[]) => void
  onSelectedMessageChange?: (msg: ChatMessageV3 | null) => void
  onSheetOpenChange?: (open: boolean) => void
  onCompareVariantsChange?: (variants: ChatPriceResponseV3[] | null) => void
}

export function useEstimateActions({
  onMessagesChange,
  onSelectedMessageChange,
  onSheetOpenChange,
  onCompareVariantsChange,
}: UseEstimateActionsOptions = {}) {
  const [feedbackState, setFeedbackState] = useState<Record<number, 'up' | 'down'>>({})
  const [estimateRecommendations, setEstimateRecommendations] = useState<
    Record<number, Array<{ id: number; source: string; rationale: string | null }>>
  >({})

  const handleFeedback = useCallback(async (estimateId: number, vote: 'up' | 'down') => {
    try {
      await estimatesApi.submitFeedback(estimateId, { vote })
      setFeedbackState(prev => ({ ...prev, [estimateId]: vote }))
    } catch {
      // Silently fail — feedback is best-effort
    }
  }, [])

  const adoptVariant = useCallback((variant: ChatPriceResponseV3) => {
    const est = variant.estimate
    if (!est) return
    const adoptMsg: ChatMessageV3 = {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: `Selected ${variant.variant_label} option: $${est.grand_total.toFixed(2)}`,
      timestamp: new Date(),
      estimate_id: variant.estimate_id,
      estimate: est,
      confidence: variant.confidence,
      confidence_label: variant.confidence_label,
    }
    onMessagesChange?.(prev => [...prev, adoptMsg])
    onSelectedMessageChange?.(adoptMsg)
    onSheetOpenChange?.(true)
    onCompareVariantsChange?.(null)
  }, [onMessagesChange, onSelectedMessageChange, onSheetOpenChange, onCompareVariantsChange])

  return {
    feedbackState,
    estimateRecommendations,
    setEstimateRecommendations,
    handleFeedback,
    adoptVariant,
  }
}
