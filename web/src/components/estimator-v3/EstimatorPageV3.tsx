'use client'

import { useState, useRef, useCallback, useEffect } from 'react'
import { useSearchParams } from 'next/navigation'
import { AnimatePresence, motion } from 'framer-motion'
import { X, DollarSign, ImagePlus, Loader2 } from 'lucide-react'

import { chatApiV3, blueprintApiV3, type ChatPriceRequestV3 } from '@/lib/api-v3'
import { ChatMessageListV3, type ChatMessageV3 } from './ChatMessageListV3'
import { EstimateBreakdownV3 } from './EstimateBreakdownV3'
import { ClarificationModal } from './ClarificationModal'
import { Send, RotateCcw } from 'lucide-react'

interface EstimatorPageV3Props {
  projectId?: number
}

export function EstimatorPageV3({ projectId }: EstimatorPageV3Props) {
  useSearchParams() // triggers suspense boundary if needed
  const [messages, setMessages] = useState<ChatMessageV3[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const [selectedMessage, setSelectedMessage] = useState<ChatMessageV3 | null>(null)
  const [sheetOpen, setSheetOpen] = useState(false)
  const [county] = useState('Dallas')
  const [clarificationQuestions, setClarificationQuestions] = useState<string[] | null>(null)
  const [attachedImage, setAttachedImage] = useState<File | null>(null)
  const [imagePreview, setImagePreview] = useState<string | null>(null)
  const [imageAnalyzing, setImageAnalyzing] = useState(false)
  const [blueprintSummary, setBlueprintSummary] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const messagesRef = useRef<ChatMessageV3[]>([])

  useEffect(() => {
    messagesRef.current = messages
  }, [messages])

  const sendMessage = useCallback(async (text?: string) => {
    const message = text ?? input
    if (!message.trim() || loading) return

    abortRef.current?.abort()
    abortRef.current = new AbortController()
    setLoading(true)
    setClarificationQuestions(null)

    const userMsg: ChatMessageV3 = {
      id: crypto.randomUUID(),
      role: 'user',
      content: message,
      timestamp: new Date(),
    }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setAttachedImage(null)
    setImagePreview(null)
    setBlueprintSummary(null)
    if (fileInputRef.current) fileInputRef.current.value = ''

    const assistantId = crypto.randomUUID()
    setMessages(prev => [...prev, {
      id: assistantId,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
    }])

    const body: ChatPriceRequestV3 = {
      message,
      county,
      history: messagesRef.current
        .filter(m => m.role === 'user' || m.role === 'assistant')
        .slice(-6)
        .map(m => ({ role: m.role, content: m.content })),
      project_id: projectId || null,
    }

    try {
      let reasoning = ''
      const toolCalls: ChatMessageV3['tool_calls'] = []
      const marketAdjustments: ChatMessageV3['market_adjustments'] = []
      let estimateData: NonNullable<ChatMessageV3['estimate']> | null = null
      let narrative = ''
      let confidence = 0.85
      let confidenceLabel = 'HIGH'
      let assumptions: string[] = []

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
        } else if (event.type === 'pricing') {
          estimateData = event.estimate as NonNullable<ChatMessageV3['estimate']>
          confidence = event.confidence
          confidenceLabel = event.confidence_label
          assumptions = event.assumptions
        } else if (event.type === 'clarification') {
          setClarificationQuestions(event.questions)
          setLoading(false)
          setMessages(prev => prev.filter(m => m.id !== assistantId))
          return
        } else if (event.type === 'token') {
          narrative += event.content
        } else if (event.type === 'error') {
          narrative += `\n[Error: ${event.message}]`
        } else if (event.type === 'done') {
          break
        }
      }

      setMessages(prev => prev.map(m =>
        m.id === assistantId
          ? {
              ...m,
              content: narrative || 'Estimate generated.',
              estimate: estimateData,
              confidence,
              confidence_label: confidenceLabel,
              assumptions,
              reasoning,
              tool_calls: toolCalls,
              market_adjustments: marketAdjustments,
            }
          : m
      ))

      if (estimateData) {
        setSelectedMessage(messagesRef.current.find(m => m.id === assistantId) || null)
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
      abortRef.current = null
    }
  }, [input, loading, county, projectId])

  const handleCopy = useCallback((id: string, content: string) => {
    navigator.clipboard.writeText(content)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 2000)
  }, [])

  const handleViewBreakdown = useCallback((msg: ChatMessageV3) => {
    setSelectedMessage(msg)
    setSheetOpen(true)
  }, [])

  const handleStopGenerating = useCallback(() => {
    abortRef.current?.abort()
    setLoading(false)
  }, [])

  const handleClarificationAnswer = useCallback((answer: string) => {
    setClarificationQuestions(null)
    setInput(answer)
    // Auto-send after a brief delay
    setTimeout(() => sendMessage(answer), 100)
  }, [sendMessage])

  const handleSuggestion = useCallback((text: string) => {
    setInput(text)
    sendMessage(text)
  }, [sendMessage])

  const handleFileSelect = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (!file.type.startsWith('image/')) return
    setAttachedImage(file)
    setImagePreview(URL.createObjectURL(file))
    setImageAnalyzing(true)
    try {
      const { data } = await blueprintApiV3.quickAnalyze(file)
      setBlueprintSummary(data.summary)
    } catch {
      setBlueprintSummary('Blueprint analysis failed — you can still describe the job.')
    } finally {
      setImageAnalyzing(false)
    }
  }, [])

  const handleRemoveImage = useCallback(() => {
    setAttachedImage(null)
    setImagePreview(null)
    setBlueprintSummary(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }, [])

  return (
    <div className="flex h-[calc(100vh-64px)] overflow-hidden">
      {/* Chat area */}
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex-1 overflow-y-auto px-4 py-6 md:px-8">
          <ChatMessageListV3
            messages={messages}
            loading={loading}
            copiedId={copiedId}
            onCopyMessage={handleCopy}
            onViewBreakdown={handleViewBreakdown}
            onStopGenerating={handleStopGenerating}
          />

          {clarificationQuestions && (
            <ClarificationModal
              questions={clarificationQuestions}
              onAnswer={handleClarificationAnswer}
              onDismiss={() => setClarificationQuestions(null)}
            />
          )}
        </div>

        <div className="shrink-0 border-t border-[color:var(--line)] bg-[color:var(--panel)] px-4 py-3">
          <div className="flex flex-wrap gap-2 mb-2">
            {['Kitchen sink rough-in, 2 fixtures', 'Water heater replacement', '3-bed house repipe'].map(hint => (
              <button
                key={hint}
                type="button"
                onClick={() => handleSuggestion(hint)}
                disabled={loading}
                className="rounded-full border border-[color:var(--line)] bg-[color:var(--panel-strong)] px-3 py-1.5 text-[11px] font-medium text-[color:var(--muted-ink)] hover:bg-[color:var(--accent-soft)] hover:text-[color:var(--accent-strong)] disabled:opacity-40 transition-colors"
              >
                {hint}
              </button>
            ))}
          </div>
          {imagePreview && (
            <div className="mb-2 flex items-center gap-2 rounded-lg border border-[color:var(--line)] bg-[color:var(--panel-strong)] p-2">
              {/* eslint-disable-next-line @next/next/no-img-element -- data URL preview, not a remote image */}
              <img src={imagePreview} alt="Blueprint preview" className="h-12 w-12 rounded-md object-cover" />
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-[color:var(--ink)] truncate">{attachedImage?.name}</p>
                {imageAnalyzing ? (
                  <p className="text-[11px] text-[color:var(--muted-ink)] flex items-center gap-1">
                    <Loader2 size={10} className="animate-spin" /> Analyzing blueprint…
                  </p>
                ) : blueprintSummary ? (
                  <p className="text-[11px] text-[color:var(--muted-ink)] truncate">{blueprintSummary}</p>
                ) : null}
              </div>
              <button
                type="button"
                onClick={handleRemoveImage}
                className="rounded-md p-1 hover:bg-[color:var(--line)]"
                aria-label="Remove image"
              >
                <X size={14} />
              </button>
            </div>
          )}
          <div className="flex items-end gap-2">
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={loading || imageAnalyzing}
              className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border border-[color:var(--line)] bg-[color:var(--panel-strong)] text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] disabled:opacity-40 transition-colors"
              aria-label="Attach blueprint image"
            >
              <ImagePlus size={18} />
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={handleFileSelect}
              className="hidden"
              aria-label="Upload blueprint image"
            />
            <textarea
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  const messageParts = [blueprintSummary, input].filter(Boolean)
                  if (messageParts.length > 1) {
                    sendMessage(`${messageParts[0]}\n\n${messageParts[1]}`)
                  } else {
                    sendMessage()
                  }
                }
              }}
              placeholder={blueprintSummary ? 'Add details or send…' : 'Describe the plumbing job...'}
              aria-label="Type a pricing question"
              rows={1}
              disabled={loading}
              className="input max-h-[120px] resize-none overflow-auto py-2.5 flex-1"
              style={{ minHeight: '46px' }}
            />
            {loading ? (
              <button
                type="button"
                onClick={handleStopGenerating}
                className="btn-primary h-11 w-11 shrink-0 rounded-2xl bg-[hsl(var(--danger))] p-0 hover:bg-[hsl(var(--danger)/0.85)]"
                aria-label="Stop generating"
              >
                <div className="flex items-center justify-center">
                  <div className="size-3 bg-white rounded-sm" />
                </div>
              </button>
            ) : (
              <button
                type="button"
                onClick={() => {
                  const messageParts = [blueprintSummary, input].filter(Boolean)
                  if (messageParts.length > 1) {
                    sendMessage(`${messageParts[0]}\n\n${messageParts[1]}`)
                  } else {
                    sendMessage()
                  }
                }}
                disabled={!input.trim() && !blueprintSummary}
                className="btn-primary h-11 w-11 shrink-0 rounded-2xl p-0 disabled:opacity-40"
                aria-label="Send message"
              >
                <Send size={16} />
              </button>
            )}
          </div>
          <div className="mt-1.5 flex items-center justify-between px-0.5">
            {messages.length > 0 ? (
              <button
                type="button"
                onClick={() => { setMessages([]); setSelectedMessage(null); setSheetOpen(false); }}
                className="inline-flex items-center gap-1.5 text-[11px] text-[color:var(--muted-ink)] transition-colors hover:text-[color:var(--ink)]"
              >
                <RotateCcw size={11} />
                New conversation
              </button>
            ) : (
              <span className="text-[11px] text-[color:var(--muted-ink)]">Enter to send · Shift+Enter for newline</span>
            )}
          </div>
        </div>
      </div>

      {/* Desktop side rail */}
      <aside className="hidden w-[360px] shrink-0 border-l border-[color:var(--line)] bg-[color:var(--panel)] lg:flex lg:flex-col">
        {selectedMessage?.estimate ? (
          <EstimateBreakdownV3
            estimate={selectedMessage.estimate}
            confidenceLabel={selectedMessage.confidence_label || 'HIGH'}
            confidenceScore={selectedMessage.confidence || 0.85}
            assumptions={selectedMessage.assumptions || []}
            county={county}
            marketAdjustments={selectedMessage.market_adjustments}
          />
        ) : (
          <div className="flex flex-1 flex-col items-center justify-center px-6 text-center text-[color:var(--muted-ink)]">
            <DollarSign size={32} className="mb-3 opacity-30" />
            <p className="text-sm font-medium">No estimate selected</p>
            <p className="mt-1 text-xs opacity-60">Send a message to generate a priced estimate.</p>
          </div>
        )}
      </aside>

      {/* Mobile bottom sheet */}
      <AnimatePresence>
        {sheetOpen && selectedMessage?.estimate && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/40 lg:hidden"
            onClick={() => setSheetOpen(false)}
          >
            <motion.div
              initial={{ y: '100%' }}
              animate={{ y: 0 }}
              exit={{ y: '100%' }}
              transition={{ type: 'spring', stiffness: 350, damping: 35 }}
              className="absolute bottom-0 left-0 right-0 max-h-[85vh] overflow-hidden rounded-t-2xl bg-[color:var(--panel)] shadow-2xl"
              onClick={e => e.stopPropagation()}
            >
              <div className="flex items-center justify-between border-b border-[color:var(--line)] px-5 py-3">
                <span className="text-sm font-semibold text-[color:var(--ink)]">Estimate Breakdown</span>
                <button type="button" onClick={() => setSheetOpen(false)} className="rounded-lg p-1.5 hover:bg-[color:var(--panel-strong)]">
                  <X size={18} className="text-[color:var(--muted-ink)]" />
                </button>
              </div>
              <div className="max-h-[calc(85vh-52px)] overflow-y-auto">
                <EstimateBreakdownV3
                  estimate={selectedMessage.estimate}
                  confidenceLabel={selectedMessage.confidence_label || 'HIGH'}
                  confidenceScore={selectedMessage.confidence || 0.85}
                  assumptions={selectedMessage.assumptions || []}
                  county={county}
                  marketAdjustments={selectedMessage.market_adjustments}
                  compact
                />
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
