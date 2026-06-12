import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useEstimateActions } from '../hooks/useEstimateActions'

const mockSubmitFeedback = vi.fn()

vi.mock('@/lib/api/estimates', () => ({
  estimatesApi: {
    submitFeedback: (...args: unknown[]) => mockSubmitFeedback(...args),
  },
}))

describe('useEstimateActions', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('has correct initial state', () => {
    const { result } = renderHook(() => useEstimateActions())
    expect(result.current.feedbackState).toEqual({})
    expect(result.current.estimateRecommendations).toEqual({})
  })

  it('handleFeedback submits vote and updates state', async () => {
    mockSubmitFeedback.mockResolvedValue({})
    const { result } = renderHook(() => useEstimateActions())

    await act(async () => {
      await result.current.handleFeedback(1, 'down')
    })

    expect(mockSubmitFeedback).toHaveBeenCalledWith(1, { vote: 'down' })
    expect(result.current.feedbackState[1]).toBe('down')
  })

  it('handleFeedback silently fails on error', async () => {
    mockSubmitFeedback.mockRejectedValue(new Error('Network error'))
    const { result } = renderHook(() => useEstimateActions())

    await act(async () => {
      await result.current.handleFeedback(1, 'up')
    })

    expect(mockSubmitFeedback).toHaveBeenCalled()
    expect(result.current.feedbackState[1]).toBeUndefined()
  })

  it('adoptVariant calls onMessagesChange and related callbacks', () => {
    const onMessagesChange = vi.fn()
    const onSelectedMessageChange = vi.fn()
    const onSheetOpenChange = vi.fn()
    const onCompareVariantsChange = vi.fn()

    const { result } = renderHook(() =>
      useEstimateActions({
        onMessagesChange: (msgs) => onMessagesChange(msgs([])),
        onSelectedMessageChange,
        onSheetOpenChange,
        onCompareVariantsChange,
      })
    )

    const variant = {
      variant_label: 'Premium',
      estimate: {
        grand_total: 500,
        labor_total: 200,
        materials_total: 200,
        tax_total: 50,
        markup_total: 50,
        misc_total: 0,
        subtotal: 500,
        line_items: [],
        market_adjustment_applied: 0,
      },
      confidence: 0.9,
      confidence_label: 'HIGH',
      estimate_id: 2,
    }

    act(() => {
      result.current.adoptVariant(variant as unknown as import('@/lib/api-v3').ChatPriceResponseV3)
    })

    expect(onMessagesChange).toHaveBeenCalled()
    expect(onSelectedMessageChange).toHaveBeenCalled()
    expect(onSheetOpenChange).toHaveBeenCalledWith(true)
    expect(onCompareVariantsChange).toHaveBeenCalledWith(null)
  })

  it('adoptVariant does nothing if estimate is missing', () => {
    const onMessagesChange = vi.fn()
    const { result } = renderHook(() =>
      useEstimateActions({ onMessagesChange: (msgs) => onMessagesChange(msgs([])) })
    )

    act(() => {
      result.current.adoptVariant({ variant_label: 'Budget', estimate: null } as unknown as import('@/lib/api-v3').ChatPriceResponseV3)
    })

    expect(onMessagesChange).not.toHaveBeenCalled()
  })

  it('setEstimateRecommendations updates recommendations state', () => {
    const { result } = renderHook(() => useEstimateActions())

    act(() => {
      result.current.setEstimateRecommendations({ 1: [{ id: 1, source: 'test', rationale: 'reason' }] })
    })

    expect(result.current.estimateRecommendations[1]).toHaveLength(1)
  })
})
