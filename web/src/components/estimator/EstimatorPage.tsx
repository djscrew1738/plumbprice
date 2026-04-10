'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { useSearchParams } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, RotateCcw, Zap, Copy, Check, FileUp, X, Square } from 'lucide-react'
import { chatApi, estimatesApi, type EstimateDetailResponse } from '@/lib/api'
import { ConfidenceBadge } from './ConfidenceBadge'
import { useToast } from '@/components/ui/Toast'
import { cn } from '@/lib/utils'
import type { ChatMessage, EstimateBreakdown as EstimateBreakdownType, LineItem } from '@/types'
import ReactMarkdown from 'react-markdown'
import { WorkspaceEntryBar, type WorkspaceEntryMode } from '@/components/workspace/WorkspaceEntryBar'
import { WorkspaceSummaryRail } from '@/components/workspace/WorkspaceSummaryRail'

const SUGGESTIONS = [
  { short: 'Toilet replace', full: 'How much to replace a toilet first floor Dallas?', hint: '$285–$485' },
  { short: 'WH attic 50G', full: 'Price to replace 50G gas water heater in attic?', hint: '$980–$1,400' },
  { short: 'Kitchen faucet', full: 'Cost for kitchen faucet replacement?', hint: '$180–$320' },
  { short: 'PRV valve', full: 'Replace PRV valve -- how much?', hint: '$380–$580' },
  { short: 'Disposal install', full: 'Garbage disposal install cost?', hint: '$220–$380' },
  { short: 'Shower valve', full: 'Replace shower valve and trim -- price?', hint: '$420–$680' },
]

const COUNTIES = ['Dallas', 'Tarrant', 'Collin', 'Denton', 'Rockwall', 'Parker']

function formatTime(d: Date) {
  return d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true })
}

function normalizeCounty(county?: string) {
  if (!county) {
    return 'Dallas'
  }

  const match = COUNTIES.find(candidate => candidate.toLowerCase() === county.toLowerCase())
  return match ?? county
}

function normalizeEntryMode(value?: string | null): WorkspaceEntryMode {
  if (value === 'upload-job-files') {
    return 'upload-job-files'
  }
  return 'quick-quote'
}

function normalizeConfidenceLabel(label?: string) {
  const upper = label?.toUpperCase()
  if (upper === 'HIGH' || upper === 'MEDIUM' || upper === 'LOW') {
    return upper
  }
  return 'HIGH'
}

function normalizeLineItems(lineItems: EstimateDetailResponse['line_items']): LineItem[] {
  if (!Array.isArray(lineItems)) {
    return []
  }

  return lineItems.map(item => ({
    line_type: item.line_type,
    description: item.description,
    quantity: item.quantity,
    unit: item.unit,
    unit_cost: item.unit_cost,
    total_cost: item.total_cost,
    supplier: item.supplier ?? undefined,
    sku: item.sku ?? undefined,
  }))
}

function toEstimateBreakdown(payload: EstimateDetailResponse): EstimateBreakdownType {
  return {
    labor_total: payload.labor_total ?? 0,
    materials_total: payload.materials_total ?? 0,
    tax_total: payload.tax_total ?? 0,
    markup_total: payload.markup_total ?? 0,
    misc_total: payload.misc_total ?? 0,
    subtotal: payload.subtotal ?? 0,
    grand_total: payload.grand_total ?? 0,
    line_items: normalizeLineItems(payload.line_items),
  }
}

export function EstimatorPage() {
  const { success, error } = useToast()
  const searchParams = useSearchParams()
  const estimateId = searchParams.get('estimateId')
  const entryParam = searchParams.get('entry')

  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [county, setCounty] = useState('Dallas')
  const [entryMode, setEntryMode] = useState<WorkspaceEntryMode>(() => normalizeEntryMode(entryParam))
  const [selectedEstimate, setSelectedEstimate] = useState<ChatMessage | null>(null)
  const [sheetOpen, setSheetOpen] = useState(false)
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const [activeSuggestion, setActiveSuggestion] = useState(0)
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)

  const [blueprintName, setBlueprintName] = useState<string | null>(null)

  const MAX_INPUT = 2000

  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const resumeErrorRef = useRef(error)
  const abortRef = useRef<AbortController | null>(null)

  const uploadMode = entryMode === 'upload-job-files'
  const showUploadPlaceholder = uploadMode && messages.length === 0 && !uploadedFile

  useEffect(() => {
    setEntryMode(normalizeEntryMode(entryParam))
  }, [entryParam])

  // Read blueprint filename from sessionStorage when landing from Blueprints page
  useEffect(() => {
    const isBlueprintEntry = searchParams.get('blueprint') === '1'
    if (isBlueprintEntry && typeof window !== 'undefined') {
      const name = sessionStorage.getItem('blueprint_filename')
      if (name) {
        setBlueprintName(name)
        sessionStorage.removeItem('blueprint_filename')
      }
    }
  }, [searchParams])

  useEffect(() => {
    resumeErrorRef.current = error
  }, [error])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  useEffect(() => {
    if (!estimateId) {
      return
    }
    const estimateIdToResume = estimateId
    const controller = new AbortController()
    let isMounted = true

    async function resumeEstimateFromQuery() {
      try {
        setLoading(true)
        const { data } = await estimatesApi.get(Number(estimateIdToResume))
        if (!isMounted) {
          return
        }

        const resumedMessage: ChatMessage = {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: `Loaded estimate #${data.id} — ${data.title || 'Saved estimate'}\n\nStatus: ${data.status}`,
          estimate: toEstimateBreakdown(data),
          confidence: data.confidence_score ?? 0,
          confidence_label: normalizeConfidenceLabel(data.confidence_label),
          assumptions: data.assumptions ?? [],
          timestamp: data.created_at ? new Date(data.created_at) : new Date(),
        }

        setCounty(normalizeCounty(data.county))
        setMessages([resumedMessage])
        setSelectedEstimate(resumedMessage)
        setSheetOpen(false)
      } catch {
        if (!isMounted) {
          return
        }

        resumeErrorRef.current('Could not load estimate', `Estimate #${estimateIdToResume} was unavailable.`)
        setSelectedEstimate(null)
        setMessages([
          {
            id: crypto.randomUUID(),
            role: 'assistant',
            content: `Could not load estimate #${estimateIdToResume}.`,
            timestamp: new Date(),
          },
        ])
      } finally {
        if (isMounted) {
          setLoading(false)
        }
      }
    }

    void resumeEstimateFromQuery()
    return () => {
      isMounted = false
      controller.abort()
    }
  }, [estimateId])

  useEffect(() => {
    if (messages.length > 0 || uploadMode) {
      return
    }
    const id = setInterval(() => setActiveSuggestion(previous => (previous + 1) % SUGGESTIONS.length), 3000)
    return () => clearInterval(id)
  }, [messages.length, uploadMode])

  const handleInputChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(event.target.value)
    event.target.style.height = 'auto'
    event.target.style.height = `${Math.min(event.target.scrollHeight, 120)}px`
  }

  const handleStopGenerating = () => {
    abortRef.current?.abort()
    abortRef.current = null
    setLoading(false)
  }

  const copyMessage = (id: string, content: string) => {
    navigator.clipboard.writeText(content).then(() => {
      setCopiedId(id)
      success('Copied to clipboard')
      setTimeout(() => setCopiedId(null), 2000)
    }).catch(() => {
      error('Failed to copy — try selecting the text manually')
    })
  }

  const sendMessage = useCallback(async (text?: string) => {
    const message = (text ?? input).trim()
    if (!message || loading || (uploadMode && !uploadedFile)) {
      return
    }
    if (message.length > MAX_INPUT) {
      return
    }

    // Cancel any previous in-flight request
    abortRef.current?.abort()
    abortRef.current = new AbortController()

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: message,
      timestamp: new Date(),
    }

    setMessages(prev => [...prev, userMsg])
    setInput('')
    if (inputRef.current) {
      inputRef.current.style.height = 'auto'
    }
    setLoading(true)

    // Build history from current messages (before this new user turn)
    const history = messages.map(m => ({ role: m.role as 'user' | 'assistant', content: m.content }))

    // Placeholder assistant message for streaming
    const streamId = crypto.randomUUID()
    setMessages(prev => [...prev, {
      id: streamId,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
    }])

    try {
      let pricingData: { estimate?: ChatMessage['estimate']; confidence?: number; confidence_label?: string; assumptions?: string[] } = {}
      let narrative = ''

      for await (const event of chatApi.priceStream({ message, county, history })) {
        if (event.type === 'pricing') {
          pricingData = {
            estimate: event.estimate ? {
              ...event.estimate,
              line_items: (event.estimate.line_items ?? []).map(item => ({
                ...item,
                supplier: item.supplier ?? undefined,
                sku: item.sku ?? undefined,
              })),
            } : undefined,
            confidence: event.confidence,
            confidence_label: event.confidence_label,
            assumptions: event.assumptions,
          }
        } else if (event.type === 'token') {
          narrative += event.token ?? ''
          setMessages(prev => prev.map(m =>
            m.id === streamId ? { ...m, content: narrative } : m
          ))
        } else if (event.type === 'done') {
          break
        }
      }

      // Finalise the streamed message with pricing metadata
      setMessages(prev => prev.map(m => {
        if (m.id !== streamId) return m
        return {
          ...m,
          content: narrative || pricingData.estimate
            ? narrative
            : 'Could not reach the API. Please check that the backend is running.',
          estimate: pricingData.estimate,
          confidence: pricingData.confidence,
          confidence_label: pricingData.confidence_label
            ? normalizeConfidenceLabel(pricingData.confidence_label)
            : 'HIGH',
          assumptions: pricingData.assumptions ?? [],
        }
      }))

      if (pricingData.estimate) {
        const finalMsg = messages.find(m => m.id === streamId)
        if (finalMsg) {
          setSelectedEstimate(finalMsg)
          setSheetOpen(true)
        }
      }
    } catch {
      setMessages(prev => prev.map(m =>
        m.id === streamId
          ? { ...m, content: 'Could not reach the API. Please check that the backend is running.' }
          : m
      ))
    } finally {
      setLoading(false)
    }
  }, [input, loading, county, uploadMode, uploadedFile, messages])

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      void sendMessage()
    }
  }

  const handleReset = () => {
    setMessages([])
    setSelectedEstimate(null)
    setSheetOpen(false)
    inputRef.current?.focus()
  }

  return (
    <div className="flex h-[calc(100dvh-54px)] flex-col">
      <WorkspaceEntryBar
        county={county}
        counties={COUNTIES}
        entryMode={entryMode}
        onCountyChange={setCounty}
        onEntryModeChange={setEntryMode}
      />

      <div className="flex min-h-0 flex-1 gap-3 px-3 pb-3 sm:gap-4 sm:px-4 sm:pb-4">
        <section className="shell-panel flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
          <div className="border-b border-[color:var(--line)] bg-[color:var(--panel-strong)] px-3 py-2.5">
            {uploadMode ? (
              <div className="shell-chip">
                <FileUp size={13} />
                Upload workflow coming next.
              </div>
            ) : (
              <div className="flex items-center gap-1.5 overflow-x-auto scrollbar-hide">
                {SUGGESTIONS.map(suggestion => (
                  <button
                    key={suggestion.short}
                    type="button"
                    onClick={() => void sendMessage(suggestion.full)}
                    disabled={loading}
                    className="shrink-0 rounded-full border border-[color:var(--line)] bg-[color:var(--panel)] px-3 py-1.5 text-[11px] font-medium text-[color:var(--muted-ink)] transition-colors hover:bg-[color:var(--accent-soft)] hover:text-[color:var(--accent-strong)] disabled:opacity-40"
                  >
                    {suggestion.short}
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="flex-1 overflow-y-auto px-3 py-4 sm:px-4">
            {showUploadPlaceholder && (
              <div className="flex h-full items-center justify-center px-4 py-8">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.png,.jpg,.jpeg,.webp"
                  className="hidden"
                  onChange={e => {
                    const f = e.target.files?.[0]
                    if (f) {
                      setUploadedFile(f)
                      setInput(`I have a job file: "${f.name}". Please help me price the plumbing work described.`)
                      setTimeout(() => inputRef.current?.focus(), 50)
                    }
                  }}
                />
                <div
                  className="w-full max-w-sm text-center cursor-pointer group"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <div className="mx-auto mb-4 flex size-16 items-center justify-center rounded-2xl border-2 border-dashed border-[color:var(--line)] bg-[color:var(--accent-soft)] text-[color:var(--accent-strong)] transition-colors group-hover:border-[color:var(--accent-strong)] group-hover:bg-[color:var(--accent-soft)]">
                    <FileUp size={26} />
                  </div>
                  <h2 className="text-xl font-semibold text-[color:var(--ink)]">Upload Job File</h2>
                  <p className="mt-2 text-sm text-[color:var(--muted-ink)]">
                    Click to browse or drag a PDF, photo, or plan sheet — then describe the scope in chat.
                  </p>
                  <p className="mt-3 text-[11px] text-[color:var(--muted-ink)] opacity-60">PDF · PNG · JPG · WEBP · up to 20 MB</p>
                </div>
              </div>
            )}

            {/* Uploaded file banner */}
            {uploadMode && uploadedFile && messages.length === 0 && (
              <div className="flex items-center gap-2.5 rounded-xl border border-[color:var(--line)] bg-[color:var(--panel-strong)] px-3 py-2.5 mb-3 text-sm">
                <FileUp size={14} className="text-[color:var(--accent-strong)] shrink-0" />
                <span className="flex-1 truncate text-[color:var(--ink)] font-medium">{uploadedFile.name}</span>
                <button
                  onClick={() => { setUploadedFile(null); setInput('') }}
                  className="p-1 rounded text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] transition-colors"
                >
                  <X size={13} />
                </button>
              </div>
            )}

            {/* Blueprint loaded banner */}
            {blueprintName && messages.length === 0 && (
              <div className="flex items-center gap-2.5 rounded-xl border border-[color:var(--line)] bg-[color:var(--accent-soft)] px-3 py-2.5 mb-3 text-sm">
                <FileUp size={14} className="text-[color:var(--accent-strong)] shrink-0" />
                <span className="flex-1 truncate text-[color:var(--ink)]">
                  Blueprint loaded: <span className="font-medium">{blueprintName}</span> — describe the scope to price it.
                </span>
                <button
                  onClick={() => setBlueprintName(null)}
                  className="p-1 rounded text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] transition-colors"
                >
                  <X size={13} />
                </button>
              </div>
            )}

            {!showUploadPlaceholder && messages.length === 0 && (
              <div className="flex h-full flex-col items-center justify-center px-4 pb-8 text-center">
                <div className="mb-5 flex size-14 items-center justify-center rounded-2xl border border-[color:var(--line)] bg-[color:var(--accent-soft)] text-[color:var(--accent-strong)]">
                  <Zap size={26} />
                </div>

                <h2 className="text-2xl font-semibold tracking-tight text-[color:var(--ink)]">DFW Plumbing Estimator</h2>
                <p className="mt-2 max-w-[320px] text-sm text-[color:var(--muted-ink)]">
                  Real pricing with labor, materials, tax, and assumptions surfaced in one workspace.
                </p>

                <div className="mb-8 mt-3 h-6 overflow-hidden">
                  <AnimatePresence mode="wait">
                    <motion.p
                      key={activeSuggestion}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -8 }}
                      transition={{ duration: 0.3 }}
                      className="text-xs font-medium text-[color:var(--accent-strong)]"
                    >
                      Try: &ldquo;{SUGGESTIONS[activeSuggestion].full}&rdquo;
                    </motion.p>
                  </AnimatePresence>
                </div>

                <div className="grid w-full max-w-sm grid-cols-2 gap-2.5">
                  {SUGGESTIONS.map((suggestion, index) => (
                    <motion.button
                      key={suggestion.short}
                      type="button"
                      onClick={() => void sendMessage(suggestion.full)}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.2, delay: index * 0.05 }}
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.97 }}
                      className="card text-left p-3"
                    >
                      <div className="text-xs font-semibold text-[color:var(--ink)]">{suggestion.short}</div>
                      <div className="mt-1 line-clamp-1 text-[10px] text-[color:var(--muted-ink)]">{suggestion.full}</div>
                      <div className="mt-1.5 text-[11px] font-bold text-[color:var(--accent-strong)]">{suggestion.hint}</div>
                    </motion.button>
                  ))}
                </div>
              </div>
            )}

            {!showUploadPlaceholder && messages.map((message, index) => (
              <motion.div
                key={message.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.18, delay: index > messages.length - 3 ? 0.04 : 0 }}
                className={cn('mb-5 flex gap-2.5 group', message.role === 'user' ? 'justify-end' : 'justify-start')}
              >
                {message.role === 'assistant' && (
                  <div className="mt-1 flex size-[26px] shrink-0 items-center justify-center rounded-full border border-[color:var(--line)] bg-[color:var(--accent-soft)] text-[9px] font-bold text-[color:var(--accent-strong)]">
                    AI
                  </div>
                )}

                <div className="flex max-w-[88%] flex-col gap-1">
                  <div className={cn('relative text-sm leading-relaxed', message.role === 'user' ? 'chat-bubble-user' : 'chat-bubble-assistant')}>
                    {message.role === 'assistant' ? (
                      <>
                        <div className="chat-prose pr-6">
                          <ReactMarkdown>{message.content}</ReactMarkdown>
                        </div>
                        <button
                          type="button"
                          onClick={() => copyMessage(message.id, message.content)}
                          className="absolute right-2 top-2 rounded-lg p-1 text-[color:var(--muted-ink)] opacity-0 transition-all hover:bg-[color:var(--panel-strong)] group-hover:opacity-100"
                          title="Copy"
                        >
                          {copiedId === message.id ? <Check size={12} className="text-emerald-500" /> : <Copy size={12} />}
                        </button>
                      </>
                    ) : (
                      message.content
                    )}

                    {message.estimate && message.confidence_label && (
                      <div className="mt-2.5 flex items-center justify-between gap-2 border-t border-[color:var(--line)] pt-2.5">
                        <ConfidenceBadge label={message.confidence_label} score={message.confidence || 0} size="sm" />
                        <button
                          type="button"
                          onClick={() => {
                            setSelectedEstimate(message)
                            setSheetOpen(true)
                          }}
                          className="text-xs font-semibold text-[color:var(--accent-strong)] transition-colors hover:text-[color:var(--accent)]"
                        >
                          View summary
                        </button>
                      </div>
                    )}
                  </div>

                  <span className={cn('text-[10px] text-[color:var(--muted-ink)] opacity-0 transition-opacity group-hover:opacity-100', message.role === 'user' ? 'text-right' : 'text-left')}>
                    {formatTime(message.timestamp)}
                  </span>
                </div>

                {message.role === 'user' && (
                  <div className="mt-1 flex size-[26px] shrink-0 items-center justify-center rounded-full border border-[color:var(--line)] bg-[color:var(--panel-strong)] text-[9px] font-bold text-[color:var(--muted-ink)]">
                    U
                  </div>
                )}
              </motion.div>
            ))}

            {!showUploadPlaceholder && loading && (
              <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="flex gap-2.5">
                <div className="flex size-[26px] shrink-0 items-center justify-center rounded-full border border-[color:var(--line)] bg-[color:var(--accent-soft)] text-[9px] font-bold text-[color:var(--accent-strong)]">
                  AI
                </div>
                <div className="chat-bubble-assistant px-4 py-3.5">
                  <div className="flex items-center gap-2">
                    <div className="flex items-center gap-1.5">
                      <div className="typing-dot" />
                      <div className="typing-dot" />
                      <div className="typing-dot" />
                    </div>
                    <button
                      type="button"
                      onClick={handleStopGenerating}
                      className="ml-2 inline-flex items-center gap-1 rounded-lg border border-[color:var(--line)] bg-[color:var(--panel)] px-2 py-1 text-[10px] font-medium text-[color:var(--muted-ink)] transition-colors hover:bg-[color:var(--panel-strong)] hover:text-[color:var(--ink)]"
                    >
                      <Square size={9} />
                      Stop
                    </button>
                  </div>
                </div>
              </motion.div>
            )}

            <div ref={bottomRef} />
          </div>

          <div className="border-t border-[color:var(--line)] bg-[color:var(--panel-strong)] px-3 pb-20 pt-2.5 lg:pb-3">
            <div className="flex items-end gap-2">
              <textarea
                ref={inputRef}
                value={input}
                onChange={handleInputChange}
                onKeyDown={handleKeyDown}
                placeholder={uploadMode && !uploadedFile ? 'Select a file above to begin…' : 'Ask a pricing question…'}
                rows={1}
                maxLength={MAX_INPUT}
                disabled={uploadMode && !uploadedFile}
                className="input max-h-[120px] resize-none overflow-auto py-2.5 disabled:cursor-not-allowed disabled:opacity-65"
                style={{ minHeight: '46px' }}
              />
              {loading ? (
                <motion.button
                  type="button"
                  onClick={handleStopGenerating}
                  whileTap={{ scale: 0.9 }}
                  className="btn-primary h-11 w-11 shrink-0 rounded-2xl bg-red-600 p-0 hover:bg-red-700"
                  aria-label="Stop generating"
                >
                  <Square size={14} />
                </motion.button>
              ) : (
                <motion.button
                  type="button"
                  onClick={() => void sendMessage()}
                  disabled={!input.trim() || (uploadMode && !uploadedFile)}
                  whileTap={{ scale: 0.9 }}
                  className="btn-primary h-11 w-11 shrink-0 rounded-2xl p-0 disabled:opacity-40"
                  aria-label="Send message"
                >
                  <Send size={16} />
                </motion.button>
              )}
            </div>
            <div className="mt-1.5 flex items-center justify-between px-0.5">
              {uploadMode && !uploadedFile ? (
                <span className="text-[11px] text-[color:var(--muted-ink)]">Select a file to unlock chat.</span>
              ) : messages.length > 0 ? (
                <button
                  type="button"
                  onClick={handleReset}
                  className="inline-flex items-center gap-1.5 text-[11px] text-[color:var(--muted-ink)] transition-colors hover:text-[color:var(--ink)]"
                >
                  <RotateCcw size={11} />
                  New conversation
                </button>
              ) : (
                <span className="text-[11px] text-[color:var(--muted-ink)]">Enter to send · Shift+Enter for newline</span>
              )}
              {input.length > 0 && (
                <span className={cn(
                  'text-[10px] tabular-nums transition-colors',
                  input.length >= MAX_INPUT ? 'text-red-500 font-semibold' : input.length > MAX_INPUT * 0.8 ? 'text-amber-500' : 'text-[color:var(--muted-ink)] opacity-60'
                )}>
                  {input.length}/{MAX_INPUT}
                </span>
              )}
            </div>
          </div>
        </section>

        <WorkspaceSummaryRail
          county={county}
          selectedEstimate={selectedEstimate}
          sheetOpen={sheetOpen}
          onSheetOpenChange={setSheetOpen}
        />
      </div>
    </div>
  )
}
