import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useChatOrchestrator } from '../hooks/useChatOrchestrator'

const mockPriceStream = vi.fn()
const mockCompare = vi.fn()
const mockListSessions = vi.fn()
const mockGetSession = vi.fn()
const mockDeleteSession = vi.fn()
const mockGetRecommendations = vi.fn()
const mockSubmitFeedback = vi.fn()

vi.mock('@/lib/api-v3', () => ({
  chatApiV3: {
    priceStream: (...args: unknown[]) => mockPriceStream(...args),
    compare: (...args: unknown[]) => mockCompare(...args),
    listSessions: (...args: unknown[]) => mockListSessions(...args),
    getSession: (...args: unknown[]) => mockGetSession(...args),
    deleteSession: (...args: unknown[]) => mockDeleteSession(...args),
  },
}))

vi.mock('@/lib/api/estimates', () => ({
  estimatesApi: {
    getRecommendations: (...args: unknown[]) => mockGetRecommendations(...args),
    submitFeedback: (...args: unknown[]) => mockSubmitFeedback(...args),
  },
}))

describe('useChatOrchestrator', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockPriceStream.mockReturnValue(
      (async function* () {
        yield { type: 'token', content: 'Hello' }
        yield { type: 'done' }
      })()
    )
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('has correct initial state', () => {
    const { result } = renderHook(() => useChatOrchestrator())
    expect(result.current.messages).toEqual([])
    expect(result.current.loading).toBe(false)
    expect(result.current.selectedMessage).toBeNull()
    expect(result.current.sheetOpen).toBe(false)
    expect(result.current.clarificationQuestions).toBeNull()
    expect(result.current.compareVariants).toBeNull()
    expect(result.current.sessions).toEqual([])
    expect(result.current.sessionsOpen).toBe(false)
    expect(result.current.suggestedContext).toEqual([])
    expect(result.current.blueprintSeeded).toBe(false)
  })

  it('handleNewConversation resets all state', () => {
    const { result } = renderHook(() => useChatOrchestrator())

    act(() => {
      result.current.handleNewConversation()
    })

    expect(result.current.messages).toEqual([])
    expect(result.current.selectedMessage).toBeNull()
    expect(result.current.sheetOpen).toBe(false)
    expect(result.current.compareVariants).toBeNull()
    expect(result.current.clarificationQuestions).toBeNull()
    expect(result.current.suggestedContext).toEqual([])
    expect(result.current.blueprintSeeded).toBe(false)
  })

  it('sendMessage adds user and assistant messages', async () => {
    const { result } = renderHook(() => useChatOrchestrator())

    await act(async () => {
      await result.current.sendMessage({ message: 'Test message' })
    })

    expect(result.current.messages.length).toBe(2)
    expect(result.current.messages[0].role).toBe('user')
    expect(result.current.messages[0].content).toBe('Test message')
    expect(result.current.messages[1].role).toBe('assistant')
  })

  it('sendMessage with compareMode calls compare API', async () => {
    mockCompare.mockResolvedValue({
      data: {
        variants: [
          { variant_label: 'Budget', estimate: { grand_total: 100, labor_total: 50, materials_total: 30, tax_total: 20, markup_total: 0, misc_total: 0, subtotal: 100, line_items: [], market_adjustment_applied: 0 }, confidence: 0.8, confidence_label: 'HIGH' },
        ],
        session_id: 123,
      },
    })

    const { result } = renderHook(() => useChatOrchestrator())

    await act(async () => {
      await result.current.sendMessage({ message: 'Compare', compareMode: true })
    })

    expect(mockCompare).toHaveBeenCalled()
    expect(result.current.compareVariants).toHaveLength(1)
  })

  it('stopGenerating aborts and resets loading', () => {
    const { result } = renderHook(() => useChatOrchestrator())

    act(() => {
      result.current.stopGenerating()
    })

    expect(result.current.loading).toBe(false)
  })

  it('loadSessions fetches and sets sessions', async () => {
    mockListSessions.mockResolvedValue({
      data: [{ id: 1, title: 'Test Session', message_count: 5, county: 'Dallas', job_type: 'Service', preferred_supplier: null, access_type: null, created_at: null, updated_at: null }],
    })

    const { result } = renderHook(() => useChatOrchestrator())

    await act(async () => {
      await result.current.loadSessions()
    })

    expect(result.current.sessions).toHaveLength(1)
    expect(result.current.sessions[0].title).toBe('Test Session')
  })

  it('handleViewBreakdown sets selected message and opens sheet', () => {
    const { result } = renderHook(() => useChatOrchestrator())
    const msg = { id: '1', role: 'assistant' as const, content: 'test', estimate: { grand_total: 100, labor_total: 50, materials_total: 30, tax_total: 20, markup_total: 0, misc_total: 0, subtotal: 100, line_items: [], market_adjustment_applied: 0 } }

    act(() => {
      result.current.handleViewBreakdown(msg)
    })

    expect(result.current.selectedMessage).toEqual(msg)
    expect(result.current.sheetOpen).toBe(true)
  })

  it('handleFeedback submits vote and updates state', async () => {
    mockSubmitFeedback.mockResolvedValue({})
    const { result } = renderHook(() => useChatOrchestrator())

    await act(async () => {
      await result.current.handleFeedback(1, 'up')
    })

    expect(mockSubmitFeedback).toHaveBeenCalledWith(1, { vote: 'up' })
    expect(result.current.feedbackState[1]).toBe('up')
  })

  it('adoptVariant creates a new message and selects it', () => {
    const { result } = renderHook(() => useChatOrchestrator())
    const variant = {
      variant_label: 'Standard',
      estimate: { grand_total: 200, labor_total: 100, materials_total: 60, tax_total: 40, markup_total: 0, misc_total: 0, subtotal: 200, line_items: [], market_adjustment_applied: 0 },
      confidence: 0.9,
      confidence_label: 'HIGH',
      estimate_id: 1,
    }

    act(() => {
      result.current.adoptVariant(variant as unknown as import('@/lib/api-v3').ChatPriceResponseV3)
    })

    expect(result.current.messages.length).toBe(1)
    expect(result.current.messages[0].content).toContain('Selected Standard')
    expect(result.current.selectedMessage?.estimate_id).toBe(1)
    expect(result.current.sheetOpen).toBe(true)
  })

  it('setters work correctly', () => {
    const { result } = renderHook(() => useChatOrchestrator())

    act(() => result.current.setSheetOpen(true))
    expect(result.current.sheetOpen).toBe(true)

    act(() => result.current.setSessionsOpen(true))
    expect(result.current.sessionsOpen).toBe(true)

    act(() => result.current.setClarificationQuestions(['Q1']))
    expect(result.current.clarificationQuestions).toEqual(['Q1'])

    act(() => result.current.setCompareVariants([]))
    expect(result.current.compareVariants).toEqual([])

    act(() => result.current.setSuggestedContext([{ field: 'county', value: 'Dallas', reason: 'test', confidence: 0.9 }]))
    expect(result.current.suggestedContext).toHaveLength(1)
  })

  it('sendMessage pauses and sets pendingIntake on intake event', async () => {
    const intake = {
      intent: 'toilet_replace',
      fixture_counts: { toilet: 2 },
      location: 'Plano',
      urgency: 'same_day',
      preferred_tier: 'standard',
      confidence: 0.85,
    }
    mockPriceStream.mockReturnValue(
      (async function* () {
        yield { type: 'intake', result: intake }
      })()
    )

    const { result } = renderHook(() => useChatOrchestrator())

    await act(async () => {
      await result.current.sendMessage({ message: '2 toilets in Plano same day' })
    })

    expect(result.current.pendingIntake).toEqual(intake)
    expect(result.current.messages[1].intake_result).toEqual(intake)
    expect(result.current.loading).toBe(false)
  })

  it('confirmIntake re-sends message with confirmed_intake', async () => {
    const intake = {
      intent: 'toilet_replace',
      fixture_counts: { toilet: 2 },
      location: 'Plano',
      urgency: 'same_day',
      preferred_tier: 'standard',
      confidence: 0.85,
    }
    mockPriceStream.mockReturnValue(
      (async function* () {
        yield { type: 'intake', result: intake }
      })()
    )

    const { result } = renderHook(() => useChatOrchestrator())

    await act(async () => {
      await result.current.sendMessage({ message: '2 toilets in Plano same day' })
    })

    mockPriceStream.mockReturnValue(
      (async function* () {
        yield { type: 'done' }
      })()
    )

    await act(async () => {
      await result.current.confirmIntake({ ...intake, fixture_counts: { toilet: 3 } })
    })

    expect(result.current.pendingIntake).toBeNull()
    // User message should not be duplicated and the intake card should be marked confirmed
    expect(result.current.messages.filter(m => m.role === 'user').length).toBe(1)
    const assistantMsg = result.current.messages.find(m => m.role === 'assistant')
    expect(assistantMsg?.intake_confirmed).toBe(true)
    const lastCall = mockPriceStream.mock.calls.at(-1)?.[0] as { confirmed_intake?: typeof intake; message: string }
    expect(lastCall.message).toBe('2 toilets in Plano same day')
    expect(lastCall.confirmed_intake?.fixture_counts.toilet).toBe(3)
  })

  it('sendMessage attaches revision suggestions to assistant message', async () => {
    mockGetRecommendations.mockResolvedValue({ data: { recommendations: [] } })
    const suggestions = [
      { id: 's1', label: 'Upgrade to tankless', action: 'upgrade', delta: {}, confidence: 0.8 },
    ]
    mockPriceStream.mockReturnValue(
      (async function* () {
        yield {
          type: 'pricing',
          estimate: { grand_total: 500, labor_total: 200, materials_total: 200, tax_total: 50, markup_total: 50, misc_total: 0, subtotal: 500, line_items: [], market_adjustment_applied: 1 },
          estimate_id: 1,
          confidence: 0.9,
          confidence_label: 'HIGH',
          assumptions: [],
          market_adjustment_applied: 1,
          revision_suggestions: suggestions,
        }
        yield { type: 'done' }
      })()
    )

    const { result } = renderHook(() => useChatOrchestrator())

    await act(async () => {
      await result.current.sendMessage({ message: 'replace water heater' })
    })

    expect(result.current.messages[1].revision_suggestions).toEqual(suggestions)
  })

})
