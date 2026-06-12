'use client'

import { useState, useRef, useCallback } from 'react'
import { chatApiV3, type ChatPriceRequestV3, type ChatPriceResponseV3, type ChatSessionV3, type SuggestedContextV3, type IntakeResultV3, type RevisionSuggestionV3 } from '@/lib/api-v3'
import { estimatesApi } from '@/lib/api/estimates'
import { haptic } from '@/lib/haptics'
import type { ChatMessageV3 } from '../ChatMessageListV3'

const REVISION_KEYWORDS = [
  'upgrade', 'downgrade', 'add', 'remove', 'swap', 'change',
  'instead of', 'switch to', 'replace with', 'make it',
  'bigger', 'smaller', 'extra', 'another', 'upsize', 'downsize',
]

function isRevisionIntent(message: string): boolean {
  return REVISION_KEYWORDS.some(kw => message.toLowerCase().includes(kw))
}

interface UseChatOrchestratorOptions {
  county?: string
  projectId?: number
}

interface SendMessagePayload {
  message: string
  compareMode?: boolean
  skipUserAppend?: boolean
  reuseAssistantId?: string
}

export function useChatOrchestrator({ county = 'Dallas', projectId }: UseChatOrchestratorOptions = {}) {
  const [messages, setMessages] = useState<ChatMessageV3[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedMessage, setSelectedMessage] = useState<ChatMessageV3 | null>(null)
  const [sheetOpen, setSheetOpen] = useState(false)
  const [clarificationQuestions, setClarificationQuestions] = useState<string[] | null>(null)
  const [suggestedContext, setSuggestedContext] = useState<SuggestedContextV3[]>([])
  const [blueprintSeeded, setBlueprintSeeded] = useState(false)
  const [compareVariants, setCompareVariants] = useState<ChatPriceResponseV3[] | null>(null)
  const [sessions, setSessions] = useState<ChatSessionV3[]>([])
  const [sessionsOpen, setSessionsOpen] = useState(false)
  const [feedbackState, setFeedbackState] = useState<Record<number, 'up' | 'down'>>({})
  const [estimateRecommendations, setEstimateRecommendations] = useState<Record<number, Array<{ id: number; source: string; rationale: string | null }>>>({})
  const [streamingMessageId, setStreamingMessageId] = useState<string | null>(null)
  const [sessionId, setSessionId] = useState<number | null>(null)
  const [pendingIntake, setPendingIntake] = useState<IntakeResultV3 | null>(null)
  const pendingIntakeMessageIdRef = useRef<string | null>(null)
  const confirmedIntakeRef = useRef<IntakeResultV3 | null>(null)

  const abortRef = useRef<AbortController | null>(null)
  const messagesRef = useRef<ChatMessageV3[]>([])
  const sessionIdRef = useRef<string | null>(null)

  // Keep messagesRef in sync
  messagesRef.current = messages

  const handleNewConversation = useCallback(() => {
    setMessages([])
    setSelectedMessage(null)
    setSheetOpen(false)
    setCompareVariants(null)
    setClarificationQuestions(null)
    setSuggestedContext([])
    setBlueprintSeeded(false)
    setSessionId(null)
    sessionIdRef.current = null
    pendingIntakeMessageIdRef.current = null
    try {
      sessionStorage.removeItem('v3_chat_session_id')
    } catch { /* noop */ }
  }, [])

  const stopGenerating = useCallback(() => {
    abortRef.current?.abort()
    setLoading(false)
  }, [])

  const sendMessage = useCallback(async (payload: SendMessagePayload) => {
    const { message, compareMode = false, skipUserAppend = false, reuseAssistantId } = payload
    if (!message.trim() || loading) return

    abortRef.current?.abort()
    abortRef.current = new AbortController()
    setLoading(true)
    setClarificationQuestions(null)
    setSuggestedContext([])
    setBlueprintSeeded(false)
    setPendingIntake(null)
    pendingIntakeMessageIdRef.current = null

    // If confirming a previous intake, include it in the request
    const confirmedIntake = confirmedIntakeRef.current
    confirmedIntakeRef.current = null

    if (!skipUserAppend) {
      const userMsg: ChatMessageV3 = {
        id: crypto.randomUUID(),
        role: 'user',
        content: message,
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, userMsg])
    }

    const assistantId = reuseAssistantId || crypto.randomUUID()
    setStreamingMessageId(assistantId)
    if (!reuseAssistantId) {
      setMessages(prev => [...prev, {
        id: assistantId,
        role: 'assistant',
        content: '',
        timestamp: new Date(),
      }])
    }

    // Detect revision intent only when we have a persisted estimate to revise
    const lastEstimateMsg = isRevisionIntent(message)
      ? messagesRef.current.slice().reverse().find(m => m.role === 'assistant' && m.estimate_id && m.estimate)
      : undefined
    const previousEstimate = lastEstimateMsg?.estimate_id
      ? {
          estimate_id: lastEstimateMsg.estimate_id,
          template_code: lastEstimateMsg.template_used ?? '',
          line_items: lastEstimateMsg.estimate!.line_items,
          grand_total: lastEstimateMsg.estimate!.grand_total,
          labor_total: lastEstimateMsg.estimate!.labor_total,
          materials_total: lastEstimateMsg.estimate!.materials_total,
        }
      : undefined

    const body: ChatPriceRequestV3 = {
      message,
      county,
      session_id: sessionIdRef.current ? Number(sessionIdRef.current) : null,
      history: messagesRef.current
        .filter(m => m.role === 'user' || m.role === 'assistant')
        .slice(-6)
        .map(m => ({ role: m.role, content: m.content })),
      project_id: projectId || null,
      previous_estimate: previousEstimate || null,
      confirmed_intake: confirmedIntake || null,
    }

    // Compare mode branch
    if (compareMode) {
      try {
        const compareBody = { ...body, variant_tiers: ['budget', 'standard', 'premium'] }
        const res = await chatApiV3.compare(compareBody)
        setCompareVariants(res.data.variants)
        if (res.data.session_id != null) {
          sessionIdRef.current = String(res.data.session_id)
          try { sessionStorage.setItem('v3_chat_session_id', String(res.data.session_id)) } catch { /* noop */ }
        }
        const compareMsg: ChatMessageV3 = {
          id: assistantId,
          role: 'assistant',
          content: `Generated ${res.data.variants.length} estimate variants for comparison.`,
          timestamp: new Date(),
          estimate: res.data.variants[1]?.estimate ?? null,
        }
        setMessages(prev => prev.map(m => m.id === assistantId ? compareMsg : m))
      } catch {
        setMessages(prev => prev.map(m =>
          m.id === assistantId
            ? { ...m, content: 'Sorry, comparison failed. Please try again.' }
            : m
        ))
      } finally {
        setLoading(false)
        abortRef.current = null
      }
      return
    }

    // Streaming branch
    try {
      let reasoning = ''
      const toolCalls: ChatMessageV3['tool_calls'] = []
      const marketAdjustments: ChatMessageV3['market_adjustments'] = []
      let estimateData: NonNullable<ChatMessageV3['estimate']> | null = null
      let estimateDiff: ChatMessageV3['estimate_diff'] = null
      let estimateId: number | null = null
      let narrative = ''
      let confidence = 0.85
      let confidenceLabel = 'HIGH'
      let assumptions: string[] = []
      let localBlueprintSeeded = false
      let intakeResult: IntakeResultV3 | null = null
      let revisionSuggestions: RevisionSuggestionV3[] | undefined
      let templateUsed: string | null = null

      for await (const event of chatApiV3.priceStream(body, abortRef.current.signal)) {
        if (event.type === 'reasoning') {
          reasoning = event.content
        } else if (event.type === 'tool_call') {
          toolCalls.push({ tool_name: event.tool, latency_ms: event.latency_ms || 0 })
        } else if (event.type === 'tool_result') {
          const existing = toolCalls.find(t => t.tool_name === event.tool)
          if (existing) {
            existing.latency_ms = event.latency_ms || existing.latency_ms
          }
        } else if (event.type === 'intake') {
          intakeResult = event.result
          setPendingIntake(event.result)
          pendingIntakeMessageIdRef.current = assistantId
          // Pause the stream so the user can confirm/edit intake
          break
        } else if (event.type === 'pricing') {
          if (event.session_id != null) {
            const sid = String(event.session_id)
            sessionIdRef.current = sid
            setSessionId(event.session_id)
            try { sessionStorage.setItem('v3_chat_session_id', sid) } catch { /* noop */ }
          }
          if (event.suggested_context && event.suggested_context.length > 0) {
            setSuggestedContext(event.suggested_context)
          }
          if (event.blueprint_seeded) {
            localBlueprintSeeded = true
            setBlueprintSeeded(true)
          }
          estimateData = event.estimate as NonNullable<ChatMessageV3['estimate']>
          estimateDiff = event.estimate_diff ?? null
          estimateId = event.estimate_id ?? null
          confidence = event.confidence
          confidenceLabel = event.confidence_label
          assumptions = event.assumptions
          revisionSuggestions = event.revision_suggestions
          templateUsed = event.template_used ?? null

          // Fetch recommendations asynchronously
          if (estimateId) {
            const eid = estimateId
            estimatesApi.getRecommendations(eid)
              .then(res => {
                if (res.data.recommendations.length > 0) {
                  setEstimateRecommendations(prev => ({
                    ...prev,
                    [eid]: res.data.recommendations,
                  }))
                }
              })
              .catch(() => { /* ignore */ })
          }

          const earlyMsg: ChatMessageV3 = {
            id: assistantId,
            role: 'assistant',
            content: '',
            timestamp: new Date(),
            estimate_id: estimateId,
            estimate: estimateData,
            estimate_diff: estimateDiff,
            confidence,
            confidence_label: confidenceLabel,
            assumptions,
            reasoning,
            tool_calls: toolCalls,
            market_adjustments: marketAdjustments,
            blueprint_seeded: localBlueprintSeeded,
            intake_result: intakeResult,
            revision_suggestions: revisionSuggestions,
            template_used: templateUsed,
          }
          setMessages(prev => prev.map(m => m.id === assistantId ? earlyMsg : m))
          setSelectedMessage(earlyMsg)
          setSheetOpen(true)
          haptic('estimate')
        } else if (event.type === 'clarification') {
          setClarificationQuestions(event.questions)
          setLoading(false)
          setMessages(prev => prev.filter(m => m.id !== assistantId))
          return
        } else if (event.type === 'token') {
          narrative += event.content
          setMessages(prev => prev.map(m =>
            m.id === assistantId ? { ...m, content: narrative } : m
          ))
        } else if (event.type === 'error') {
          narrative += `\n[Error: ${event.message}]`
        } else if (event.type === 'done') {
          break
        }
      }

      const finalMsg: Partial<ChatMessageV3> = {
        content: narrative || (estimateData ? 'Estimate generated.' : ''),
        estimate_id: estimateId ?? undefined,
        estimate: estimateData ?? undefined,
        estimate_diff: estimateDiff ?? undefined,
        confidence,
        confidence_label: confidenceLabel,
        assumptions,
        reasoning,
        tool_calls: toolCalls,
        market_adjustments: marketAdjustments,
        blueprint_seeded: localBlueprintSeeded,
        intake_result: intakeResult,
        revision_suggestions: revisionSuggestions,
        template_used: templateUsed,
      }
      setMessages(prev => prev.map(m =>
        m.id === assistantId ? { ...m, ...finalMsg } : m
      ))
      setSelectedMessage(prev =>
        prev?.id === assistantId ? { ...prev, ...finalMsg } : prev
      )

      if (estimateData) {
        setSelectedMessage(prev => prev ?? (messagesRef.current.find(m => m.id === assistantId) || null))
        setSheetOpen(true)
      }
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        setMessages(prev => prev.map(m =>
          m.id === assistantId
            ? { ...m, content: 'Sorry, something went wrong. Please try again.' }
            : m
        ))
      }
    } finally {
      setLoading(false)
      setStreamingMessageId(null)
      abortRef.current = null
    }
  }, [loading, county, projectId])

  const confirmIntake = useCallback((confirmed: IntakeResultV3) => {
    confirmedIntakeRef.current = confirmed
    setPendingIntake(null)
    const intakeMsgId = pendingIntakeMessageIdRef.current
    pendingIntakeMessageIdRef.current = null
    // Mark the intake card as confirmed so it disappears; do not duplicate the user message
    if (intakeMsgId) {
      setMessages(prev => prev.map(m => m.id === intakeMsgId ? { ...m, intake_confirmed: true } : m))
    }
    const lastUserMsg = messagesRef.current.slice().reverse().find(m => m.role === 'user')
    if (lastUserMsg) {
      sendMessage({ message: lastUserMsg.content, skipUserAppend: true, reuseAssistantId: intakeMsgId || undefined })
    }
  }, [sendMessage])

  const editMessage = useCallback((messageId: string, onEdit: (content: string) => void) => {
    const msg = messagesRef.current.find(m => m.id === messageId)
    if (!msg || msg.role !== 'user') return
    // Remove this message and all messages after it
    const index = messagesRef.current.findIndex(m => m.id === messageId)
    setMessages(prev => prev.slice(0, index))
    onEdit(msg.content)
  }, [])

  const regenerateMessage = useCallback((messageId: string, onRegenerate: (message: string) => void) => {
    // Find the user message that preceded this assistant message
    const msgIndex = messagesRef.current.findIndex(m => m.id === messageId)
    if (msgIndex <= 0) return
    // Find the nearest user message before this assistant message
    let userMsgIndex = msgIndex - 1
    while (userMsgIndex >= 0 && messagesRef.current[userMsgIndex].role !== 'user') {
      userMsgIndex--
    }
    if (userMsgIndex < 0) return
    const userMsg = messagesRef.current[userMsgIndex]
    // Remove from user message onward
    setMessages(prev => prev.slice(0, userMsgIndex))
    onRegenerate(userMsg.content)
  }, [])

  const deleteMessage = useCallback((messageId: string) => {
    const index = messagesRef.current.findIndex(m => m.id === messageId)
    if (index < 0) return
    setMessages(prev => prev.filter(m => m.id !== messageId))
  }, [])

  const handleFeedback = useCallback(async (estimateId: number, vote: 'up' | 'down') => {
    try {
      await estimatesApi.submitFeedback(estimateId, { vote })
      setFeedbackState(prev => ({ ...prev, [estimateId]: vote }))
    } catch {
      // Silently fail — feedback is best-effort
    }
  }, [])

  const loadSessions = useCallback(async () => {
    try {
      const res = await chatApiV3.listSessions({ limit: 20 })
      setSessions(res.data)
    } catch {
      setSessions([])
    }
  }, [])

  const handleClarificationAnswer = useCallback((answer: string, onSend: (msg: string) => void) => {
    setClarificationQuestions(null)
    onSend(answer)
  }, [])

  const handleViewBreakdown = useCallback((msg: ChatMessageV3) => {
    setSelectedMessage(msg)
    setSheetOpen(true)
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
    setMessages(prev => [...prev, adoptMsg])
    setSelectedMessage(adoptMsg)
    setSheetOpen(true)
    setCompareVariants(null)
  }, [])

  // Restore session from sessionStorage on mount
  const restoreSession = useCallback(() => {
    try {
      const stored = sessionStorage.getItem('v3_chat_session_id')
      if (stored) {
        sessionIdRef.current = stored
      }
    } catch {
      // sessionStorage may be unavailable
    }
  }, [])

  return {
    // State
    messages,
    loading,
    selectedMessage,
    sheetOpen,
    clarificationQuestions,
    suggestedContext,
    blueprintSeeded,
    compareVariants,
    sessions,
    sessionsOpen,
    feedbackState,
    estimateRecommendations,
    pendingIntake,

    // Actions
    sendMessage,
    confirmIntake,
    stopGenerating,
    handleNewConversation,
    loadSessions,
    handleClarificationAnswer,
    handleViewBreakdown,
    handleFeedback,
    adoptVariant,
    restoreSession,

    // Message actions
    editMessage,
    regenerateMessage,
    deleteMessage,
    streamingMessageId,

    // Session id
    sessionId,

    // Setters
    setSelectedMessage,
    setSheetOpen,
    setSessionsOpen,
    setClarificationQuestions,
    setCompareVariants,
    setSuggestedContext,
    setMessages,
    setSessions,
    setPendingIntake,
    sessionIdRef,
  }
}
