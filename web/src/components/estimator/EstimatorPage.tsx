'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { useSearchParams } from 'next/navigation'
import { FileUp, X } from 'lucide-react'
import { chatApi, estimatesApi, sessionsApi, templatesApi, type EstimateDetailResponse, type PricingTemplateSummary } from '@/lib/api'
import { useToast } from '@/components/ui/Toast'
import type { ChatMessage, EstimateBreakdown as EstimateBreakdownType, LineItem } from '@/types'
import { WorkspaceEntryBar, type WorkspaceEntryMode } from '@/components/workspace/WorkspaceEntryBar'
// EstimateBreakdownRail role is fulfilled by WorkspaceSummaryRail, which wraps
// EstimateBreakdown.tsx with desktop aside + mobile bottom-sheet behaviour.
// Creating a separate EstimateBreakdownRail would duplicate that logic, so we
// reuse WorkspaceSummaryRail directly.
import { WorkspaceSummaryRail } from '@/components/workspace/WorkspaceSummaryRail'
import { SuggestionGrid } from './SuggestionGrid'
import { SuggestionChipBar } from './SuggestionChipBar'
import { ChatMessageList } from './ChatMessageList'
import { ChatInputBar } from './ChatInputBar'
import { TemplateBrowser } from './TemplateBrowser'

const SUGGESTIONS = [
  { short: 'Toilet replace', full: 'How much to replace a toilet first floor Dallas?', hint: '$285–$485' },
  { short: 'WH attic 50G', full: 'Price to replace 50G gas water heater in attic?', hint: '$980–$1,400' },
  { short: 'Kitchen faucet', full: 'Cost for kitchen faucet replacement?', hint: '$180–$320' },
  { short: 'PRV valve', full: 'Replace PRV valve -- how much?', hint: '$380–$580' },
  { short: 'Disposal install', full: 'Garbage disposal install cost?', hint: '$220–$380' },
  { short: 'Shower valve', full: 'Replace shower valve and trim -- price?', hint: '$420–$680' },
]

const COUNTIES = ['Dallas', 'Tarrant', 'Collin', 'Denton', 'Rockwall', 'Parker']

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
  const sessionParam = searchParams.get('session')

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
  const [sessionId, setSessionId] = useState<number | null>(null)
  const [pricingTemplates, setPricingTemplates] = useState<PricingTemplateSummary[]>([])
  const [keyboardOffset, setKeyboardOffset] = useState(0)
  const [templateBrowserOpen, setTemplateBrowserOpen] = useState(false)
  const [editingMessageId, setEditingMessageId] = useState<string | null>(null)

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

  // Track on-screen keyboard height to prevent input overlap on iOS/Android
  useEffect(() => {
    const viewport = window.visualViewport
    if (!viewport) return
    const handler = () => {
      const offset = window.innerHeight - viewport.height - viewport.offsetTop
      setKeyboardOffset(Math.max(0, offset))
    }
    viewport.addEventListener('resize', handler)
    viewport.addEventListener('scroll', handler)
    return () => {
      viewport.removeEventListener('resize', handler)
      viewport.removeEventListener('scroll', handler)
    }
  }, [])

  useEffect(() => {
    let active = true
    templatesApi.list().then(res => {
      if (active) setPricingTemplates(res.data)
    }).catch(() => {})
    return () => { active = false }
  }, [])

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

  // Resume from a previous chat session via ?session={id}
  useEffect(() => {
    if (!sessionParam || estimateId) return
    const sid = Number(sessionParam)
    if (!sid || isNaN(sid)) return

    let isMounted = true
    async function resumeSession() {
      try {
        setLoading(true)
        const { data } = await sessionsApi.get(sid)
        if (!isMounted) return

        setSessionId(sid)
        if (data.county) setCounty(normalizeCounty(data.county))

        const resumed: ChatMessage[] = (data.messages ?? []).map((m) => ({
          id: crypto.randomUUID(),
          role: m.role,
          content: m.content,
          timestamp: m.created_at ? new Date(m.created_at) : new Date(),
        }))
        setMessages(resumed)
      } catch {
        if (!isMounted) return
        resumeErrorRef.current('Could not load session', `Session #${sid} was unavailable.`)
        setMessages([
          {
            id: crypto.randomUUID(),
            role: 'assistant',
            content: `Could not load session #${sid}.`,
            timestamp: new Date(),
          },
        ])
      } finally {
        if (isMounted) setLoading(false)
      }
    }

    void resumeSession()
    return () => { isMounted = false }
  }, [sessionParam, estimateId])

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

  const handleViewBreakdown = useCallback((message: ChatMessage) => {
    setSelectedEstimate(message)
    setSheetOpen(true)
  }, [])

  const handleTemplateSelect = useCallback(async (id: string) => {
    try {
      const { data: tpl } = await templatesApi.get(id)
      const price = tpl.base_price != null ? ` (~$${tpl.base_price})` : ''
      const prompt = `Price for ${tpl.name} (SKU: ${tpl.sku ?? 'N/A'}) in ${county}?${price}`
      setInput(prompt)
      inputRef.current?.focus()
    } catch { /* ignore */ }
  }, [county])

  const handleTemplateBrowserSelect = useCallback((template: PricingTemplateSummary) => {
    const price = template.base_price != null ? ` (~$${template.base_price})` : ''
    const tags = template.tags?.length ? ` [${template.tags.join(', ')}]` : ''
    const prompt = `Price for ${template.name}${tags} in ${county}?${price}`
    setInput(prompt)
    setTemplateBrowserOpen(false)
    inputRef.current?.focus()
  }, [county])

  const handleEditLineItems = useCallback((messageId: string) => {
    setEditingMessageId(messageId)
  }, [])

  const handleSaveLineItems = useCallback((messageId: string, lineItems: LineItem[]) => {
    setMessages(prev => prev.map(m => {
      if (m.id !== messageId || !m.estimate) return m
      const laborTotal = lineItems.filter(i => i.line_type === 'labor').reduce((s, i) => s + i.total_cost, 0)
      const materialsTotal = lineItems.filter(i => i.line_type === 'material').reduce((s, i) => s + i.total_cost, 0)
      const markupTotal = lineItems.filter(i => i.line_type === 'markup').reduce((s, i) => s + i.total_cost, 0)
      const taxTotal = lineItems.filter(i => i.line_type === 'tax').reduce((s, i) => s + i.total_cost, 0)
      const miscTotal = lineItems.filter(i => i.line_type === 'misc').reduce((s, i) => s + i.total_cost, 0)
      const subtotal = laborTotal + materialsTotal + markupTotal + miscTotal
      const grandTotal = subtotal + taxTotal

      const updated: ChatMessage = {
        ...m,
        estimate: {
          labor_total: laborTotal,
          materials_total: materialsTotal,
          markup_total: markupTotal,
          tax_total: taxTotal,
          misc_total: miscTotal,
          subtotal,
          grand_total: grandTotal,
          line_items: lineItems,
        },
      }

      // Keep workspace rail in sync
      if (selectedEstimate?.id === messageId) {
        setSelectedEstimate(updated)
      }

      return updated
    }))
    setEditingMessageId(null)
  }, [selectedEstimate])

  const handleCancelEditLineItems = useCallback(() => {
    setEditingMessageId(null)
  }, [])

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

      for await (const event of chatApi.priceStream({ message, county, history, session_id: sessionId })) {
        if (event.type === 'pricing') {
          if (event.session_id != null) setSessionId(event.session_id)
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
        } else if (event.type === 'error') {
          narrative += event.error ?? ''
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
        const finalContent = narrative
          || (pricingData.estimate ? 'Pricing complete — see the breakdown below.' : 'Could not reach the API. Please check that the backend is running.')
        return {
          ...m,
          content: finalContent,
          estimate: pricingData.estimate,
          confidence: pricingData.confidence,
          confidence_label: pricingData.confidence_label
            ? normalizeConfidenceLabel(pricingData.confidence_label)
            : 'HIGH',
          assumptions: pricingData.assumptions ?? [],
        }
      }))

      if (pricingData.estimate) {
        setMessages(prev => {
          const finalMsg = prev.find(m => m.id === streamId)
          if (finalMsg) {
            setSelectedEstimate(finalMsg)
            setSheetOpen(true)
          }
          return prev
        })
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
  }, [input, loading, county, uploadMode, uploadedFile, messages, sessionId])

  const handleKeyDown = useCallback((event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      void sendMessage()
    }
  }, [sendMessage])

  const handleReset = useCallback(() => {
    setMessages([])
    setSelectedEstimate(null)
    setSheetOpen(false)
    setSessionId(null)
    inputRef.current?.focus()
  }, [])

  return (
    <div className="flex flex-col" style={{ height: `calc(100dvh - 54px - ${keyboardOffset}px)` }}>
      <WorkspaceEntryBar
        county={county}
        counties={COUNTIES}
        entryMode={entryMode}
        onCountyChange={setCounty}
        onEntryModeChange={setEntryMode}
      />

      <div className="flex min-h-0 flex-1 gap-3 px-3 pb-3 sm:gap-4 sm:px-4 sm:pb-4">
        <section className="shell-panel flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
          <SuggestionChipBar
            suggestions={SUGGESTIONS}
            uploadMode={uploadMode}
            loading={loading}
            pricingTemplates={pricingTemplates}
            onSendMessage={(text) => void sendMessage(text)}
            onTemplateSelect={handleTemplateSelect}
            onOpenTemplateBrowser={() => setTemplateBrowserOpen(true)}
          />

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
                  className="flex min-h-[32px] min-w-[32px] items-center justify-center rounded-lg p-2 text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] transition-colors"
                  aria-label="Clear uploaded file"
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
                  className="flex min-h-[32px] min-w-[32px] items-center justify-center rounded-lg p-2 text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] transition-colors"
                  aria-label="Clear loaded blueprint"
                >
                  <X size={13} />
                </button>
              </div>
            )}

            {!showUploadPlaceholder && messages.length === 0 && (
              <SuggestionGrid
                suggestions={SUGGESTIONS}
                activeSuggestion={activeSuggestion}
                onSelect={(text) => void sendMessage(text)}
              />
            )}

            {!showUploadPlaceholder && (
              <ChatMessageList
                messages={messages}
                loading={loading}
                copiedId={copiedId}
                editingMessageId={editingMessageId}
                onCopyMessage={copyMessage}
                onViewBreakdown={handleViewBreakdown}
                onStopGenerating={handleStopGenerating}
                onEditLineItems={handleEditLineItems}
                onSaveLineItems={handleSaveLineItems}
                onCancelEditLineItems={handleCancelEditLineItems}
              />
            )}

            <div ref={bottomRef} />
          </div>

          <ChatInputBar
            input={input}
            loading={loading}
            uploadMode={uploadMode}
            uploadedFile={uploadedFile}
            hasMessages={messages.length > 0}
            maxInput={MAX_INPUT}
            onInputChange={handleInputChange}
            onKeyDown={handleKeyDown}
            onSend={() => void sendMessage()}
            onStopGenerating={handleStopGenerating}
            onReset={handleReset}
            inputRef={inputRef}
          />
        </section>

        <WorkspaceSummaryRail
          county={county}
          selectedEstimate={selectedEstimate}
          sheetOpen={sheetOpen}
          onSheetOpenChange={setSheetOpen}
        />
      </div>

      <TemplateBrowser
        open={templateBrowserOpen}
        onClose={() => setTemplateBrowserOpen(false)}
        onSelect={handleTemplateBrowserSelect}
      />
    </div>
  )
}
