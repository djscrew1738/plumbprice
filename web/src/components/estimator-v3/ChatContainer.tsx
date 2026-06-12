'use client'

import { useState, useCallback } from 'react'
import dynamic from 'next/dynamic'
import { AnimatePresence, motion } from 'framer-motion'
import { X, DollarSign, ImagePlus, Loader2, ZoomIn, Send, RotateCcw, History, Trash2 } from 'lucide-react'
import { cn } from '@/lib/utils'

import { type ChatPriceResponseV3, type ChatSessionV3, type SuggestedContextV3, type IntakeResultV3, type RevisionSuggestionV3 } from '@/lib/api-v3'
import { ChatMessageListV3, type ChatMessageV3 } from './ChatMessageListV3'
import { Modal } from '@/components/ui/Modal'
import { haptic } from '@/lib/haptics'
import { ShareDialog } from './ShareDialog'
import { PresenceIndicator } from './PresenceIndicator'
import { TemplatePicker } from './TemplatePicker'
import { TemplateEditor } from './TemplateEditor'
import { FieldModeToggle } from './FieldModeToggle'

const EstimateBreakdownV3 = dynamic(
  () => import('./EstimateBreakdownV3').then(m => ({ default: m.EstimateBreakdownV3 })),
  { ssr: false }
)
const ClarificationModal = dynamic(
  () => import('./ClarificationModal').then(m => ({ default: m.ClarificationModal })),
  { ssr: false }
)
const EstimateVersionTimeline = dynamic(
  () => import('./EstimateVersionTimeline').then(m => ({ default: m.EstimateVersionTimeline })),
  { ssr: false }
)

interface ChatContainerProps {
  keyboardOffset?: number
  county?: string

  // Messages
  messages: ChatMessageV3[]
  loading: boolean
  onStopGenerating: () => void

  // Selection
  selectedMessage: ChatMessageV3 | null
  sheetOpen: boolean
  onSetSheetOpen: (open: boolean) => void
  onViewBreakdown: (msg: ChatMessageV3) => void

  // Copy
  copiedId: string | null
  onCopyMessage: (id: string, content: string) => void

  // Feedback
  onFeedback?: (estimateId: number, vote: 'up' | 'down') => void
  feedbackState?: Record<number, 'up' | 'down'>
  estimateRecommendations?: Record<number, Array<{ id: number; source: string; rationale: string | null }>>

  // Input
  input: string
  setInput: (v: string) => void
  onSubmit: () => void
  handleKeyDown: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void
  inputRef: React.RefObject<HTMLTextAreaElement | null>
  disabled: boolean

  // Image
  imagePreview: string | null
  imageAnalyzing: boolean
  blueprintSummary: string | null
  attachedImage: File | null
  onRemoveImage: () => void
  fileInputRef: React.RefObject<HTMLInputElement | null>
  onFileSelect: (file: File | undefined) => void

  // Voice
  speechSupported: boolean
  speechListening: boolean
  onToggleSpeech: () => void
  voiceReadBack: boolean
  onToggleVoiceReadBack: () => void
  ttsSupported: boolean

  // Suggestions
  suggestedContext: SuggestedContextV3[]
  onDismissSuggestions: () => void
  onSuggestionClick: (text: string) => void
  hintButtons?: string[]

  // Compare
  compareMode: boolean
  onToggleCompareMode: () => void
  compareVariants: ChatPriceResponseV3[] | null
  onDismissCompare: () => void
  onAdoptVariant: (variant: ChatPriceResponseV3) => void

  // Sessions
  sessions: ChatSessionV3[]
  sessionsOpen: boolean
  onSetSessionsOpen: (open: boolean) => void
  onLoadSessions: () => void
  onSelectSession: (sessionId: number, messages: ChatMessageV3[], sessionIdStr: string) => void
  onDeleteSession: (sessionId: number) => void

  // Conversation
  onNewConversation: () => void

  // Clarification
  clarificationQuestions: string[] | null
  onClarificationAnswer: (answer: string) => void
  onDismissClarification: () => void
  // Sprint 2: message actions
  onEditMessage?: (id: string, content: string) => void
  onRegenerateMessage?: (id: string) => void
  onDeleteMessage?: (id: string) => void
  streamingMessageId?: string | null
  onRefine?: (prompt: string) => void
  // v6.6.0 intake + proactive suggestions
  pendingIntake?: IntakeResultV3 | null
  onConfirmIntake?: (intake: IntakeResultV3) => void
  onRevisionSuggestionClick?: (suggestion: RevisionSuggestionV3) => void
  // Sprint 5: sharing
  sessionId?: number | null
}

export function ChatContainer({
  keyboardOffset = 0,
  county = 'Dallas',
  messages,
  loading,
  onStopGenerating,
  selectedMessage,
  sheetOpen,
  onSetSheetOpen,
  onViewBreakdown,
  copiedId,
  onCopyMessage,
  onFeedback,
  feedbackState,
  estimateRecommendations,
  input,
  setInput,
  onSubmit,
  handleKeyDown,
  inputRef,
  disabled,
  imagePreview,
  imageAnalyzing,
  blueprintSummary,
  attachedImage,
  onRemoveImage,
  fileInputRef,
  onFileSelect,
  speechSupported,
  speechListening,
  onToggleSpeech,
  voiceReadBack,
  onToggleVoiceReadBack,
  ttsSupported,
  suggestedContext,
  onDismissSuggestions,
  onSuggestionClick,
  hintButtons = ['Kitchen sink rough-in, 2 fixtures', 'Water heater replacement', '3-bed house repipe'],
  compareMode,
  onToggleCompareMode,
  compareVariants,
  onDismissCompare,
  onAdoptVariant,
  sessions,
  sessionsOpen,
  onSetSessionsOpen,
  onLoadSessions,
  onSelectSession,
  onDeleteSession,
  onNewConversation,
  clarificationQuestions,
  onClarificationAnswer,
  onDismissClarification,
  onEditMessage,
  onRegenerateMessage,
  onDeleteMessage,
  streamingMessageId,
  onRefine,
  pendingIntake,
  onConfirmIntake,
  onRevisionSuggestionClick,
  sessionId,
}: ChatContainerProps) {
  const isInputDisabled = disabled || !!pendingIntake
  const [imagePreviewOpen, setImagePreviewOpen] = useState(false)
  const [shareOpen, setShareOpen] = useState(false)
  const [templateEditorOpen, setTemplateEditorOpen] = useState(false)

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    onFileSelect(e.target.files?.[0])
  }, [onFileSelect])

  return (
    <div className="flex overflow-hidden" style={{ height: `calc(100dvh - 64px - ${keyboardOffset}px)` }}>
      {/* Chat area */}
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex-1 overflow-y-auto px-4 py-6 md:px-8">
          <div className="flex items-center justify-between px-4 py-2 md:px-8">
            <div className="flex items-center gap-2">
              <FieldModeToggle />
              <PresenceIndicator />
            </div>
            {sessionId && (
              <button
                type="button"
                onClick={() => setShareOpen(true)}
                className="text-[11px] font-medium text-[color:var(--accent-strong)] hover:underline"
              >
                Share
              </button>
            )}
          </div>
          <ChatMessageListV3
            messages={messages}
            loading={loading}
            copiedId={copiedId}
            onCopyMessage={onCopyMessage}
            onViewBreakdown={onViewBreakdown}
            onStopGenerating={onStopGenerating}
            onFeedback={onFeedback}
            feedbackState={feedbackState}
            estimateRecommendations={estimateRecommendations}
            onEditMessage={onEditMessage}
            onRegenerateMessage={onRegenerateMessage}
            onDeleteMessage={onDeleteMessage}
            streamingMessageId={streamingMessageId}
            onRefine={onRefine}
            onConfirmIntake={onConfirmIntake}
            onSuggestionClick={onRevisionSuggestionClick}
          />

          {clarificationQuestions && (
            <ClarificationModal
              questions={clarificationQuestions}
              onAnswer={onClarificationAnswer}
              onDismiss={onDismissClarification}
            />
          )}

          {/* Compare variants panel */}
          {compareVariants && compareVariants.length > 0 && (
            <div className="mt-4 rounded-xl border border-[color:var(--line)] bg-[color:var(--panel-strong)] p-4">
              <div className="mb-3 flex items-center justify-between">
                <span className="text-sm font-semibold text-[color:var(--ink)]">Estimate Comparison</span>
                <button
                  type="button"
                  onClick={onDismissCompare}
                  className="rounded-lg p-1 text-[color:var(--muted-ink)] hover:bg-[color:var(--line)]"
                  aria-label="Dismiss comparison"
                >
                  <X size={14} />
                </button>
              </div>
              <div className="flex gap-3 overflow-x-auto pb-2">
                {compareVariants.map((variant, idx) => {
                  const est = variant.estimate
                  if (!est) return null
                  const isStandard = variant.variant_label === 'Standard'
                  return (
                    <div
                      key={idx}
                      className={cn(
                        'min-w-[200px] flex-1 rounded-lg border p-3',
                        isStandard
                          ? 'border-[color:var(--accent)] bg-[color:var(--accent-soft)]/20'
                          : 'border-[color:var(--line)] bg-[color:var(--panel)]'
                      )}
                    >
                      <div className="mb-2 flex items-center justify-between">
                        <span className={cn(
                          'text-[10px] font-bold uppercase tracking-wider',
                          variant.variant_label === 'Budget' && 'text-emerald-600',
                          variant.variant_label === 'Premium' && 'text-amber-600',
                          isStandard && 'text-[color:var(--accent-strong)]'
                        )}>
                          {variant.variant_label || 'Variant'}
                        </span>
                        {isStandard && <span className="text-[10px] text-[color:var(--accent-strong)]">★ Recommended</span>}
                      </div>
                      <p className="text-lg font-bold text-[color:var(--ink)]">
                        ${est.grand_total.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </p>
                      <div className="mt-2 space-y-1 text-[11px] text-[color:var(--muted-ink)]">
                        <div className="flex justify-between"><span>Labor</span><span>${est.labor_total.toFixed(2)}</span></div>
                        <div className="flex justify-between"><span>Materials</span><span>${est.materials_total.toFixed(2)}</span></div>
                        <div className="flex justify-between"><span>Tax</span><span>${est.tax_total.toFixed(2)}</span></div>
                      </div>
                      <button
                        type="button"
                        onClick={() => {
                          haptic('tap')
                          onAdoptVariant(variant)
                        }}
                        className="mt-3 w-full rounded-lg bg-[color:var(--accent)] px-2 py-1.5 text-[11px] font-semibold text-white hover:opacity-90 transition-opacity"
                      >
                        Select
                      </button>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          <div ref={(el) => { if (el) el.scrollIntoView({ behavior: 'smooth' }) }} />
        </div>

        {/* Input area */}
        <div className="shrink-0 border-t border-[color:var(--line)] bg-[color:var(--panel)] px-4 py-3 pb-[max(calc(env(safe-area-inset-bottom)+12px),12px)] lg:pb-3">
          {/* Suggested context chips */}
          {suggestedContext.length > 0 && (
            <div className="mb-2 flex flex-wrap gap-2">
              {suggestedContext.map((s, idx) => (
                <button
                  key={`${s.field}-${idx}`}
                  type="button"
                  onClick={() => {
                    haptic('tap')
                    const phrase = `${s.field}: ${s.value}`
                    if (input.trim().toLowerCase().includes(phrase.toLowerCase())) return
                    setInput(input.trim() ? `${input.trim()}, ${phrase}` : phrase)
                  }}
                  className="rounded-full border border-[color:var(--accent-soft)] bg-[color:var(--accent-soft)]/30 px-3 py-1.5 text-[11px] font-medium text-[color:var(--accent-strong)] hover:bg-[color:var(--accent-soft)] transition-colors"
                  title={s.reason}
                >
                  💡 {s.field}: {s.value}
                  {s.confidence >= 0.8 && <span className="ml-1">★</span>}
                </button>
              ))}
              <button
                type="button"
                onClick={onDismissSuggestions}
                className="rounded-full px-2 py-1.5 text-[11px] text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] transition-colors"
                aria-label="Dismiss suggestions"
              >
                <X size={12} />
              </button>
            </div>
          )}

          {/* Compare mode toggle + quick hints */}
          <div className="flex items-center justify-between gap-2 mb-2">
            <div className="flex flex-wrap gap-2">
              {hintButtons.map(hint => (
                <button
                  key={hint}
                  type="button"
                  onClick={() => onSuggestionClick(hint)}
                  disabled={isInputDisabled}
                  className="rounded-full border border-[color:var(--line)] bg-[color:var(--panel-strong)] px-3 py-2 text-[11px] font-medium text-[color:var(--muted-ink)] hover:bg-[color:var(--accent-soft)] hover:text-[color:var(--accent-strong)] disabled:opacity-40 transition-colors min-h-[44px] min-w-[44px]"
                >
                  {hint}
                </button>
              ))}
            </div>
            <button
              type="button"
              onClick={() => { haptic('tap'); onToggleCompareMode() }}
              disabled={isInputDisabled}
              className={cn(
                'rounded-full border px-3 py-2 text-[11px] font-medium transition-colors min-h-[44px] min-w-[44px] disabled:opacity-40',
                compareMode
                  ? 'border-[color:var(--accent)] bg-[color:var(--accent)] text-white'
                  : 'border-[color:var(--line)] bg-[color:var(--panel-strong)] text-[color:var(--muted-ink)] hover:bg-[color:var(--accent-soft)] hover:text-[color:var(--accent-strong)]'
              )}
              title={compareMode ? 'Compare mode active — generates 3 variants' : 'Toggle compare mode'}
            >
              📊 Compare
            </button>
          </div>

          {/* Image preview */}
          {imagePreview && (
            <div className="mb-2 flex items-center gap-2 rounded-lg border border-[color:var(--line)] bg-[color:var(--panel-strong)] p-2">
              <button
                type="button"
                onClick={() => setImagePreviewOpen(true)}
                className="relative shrink-0"
                aria-label="Preview image"
              >
                {/* eslint-disable-next-line @next/next/no-img-element -- data URL preview, not a remote image */}
                <img src={imagePreview} alt="Blueprint preview" className="h-12 w-12 rounded-md object-cover" />
                <div className="absolute inset-0 flex items-center justify-center rounded-md bg-black/30 opacity-0 hover:opacity-100 transition-opacity">
                  <ZoomIn size={14} className="text-white" />
                </div>
              </button>
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
                onClick={onRemoveImage}
                className="rounded-md p-1 hover:bg-[color:var(--line)] min-h-[44px] min-w-[44px] flex items-center justify-center"
                aria-label="Remove image"
              >
                <X size={14} />
              </button>
            </div>
          )}

          {/* Composer row */}
          <div className="flex items-end gap-2">
            <TemplatePicker
              onSelect={text => {
                if (isInputDisabled) return
                setInput(input.trim() ? `${input.trim()} ${text}` : text)
              }}
              onOpenEditor={() => {
                if (isInputDisabled) return
                setTemplateEditorOpen(true)
              }}
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={isInputDisabled || imageAnalyzing}
              className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border border-[color:var(--line)] bg-[color:var(--panel-strong)] text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] disabled:opacity-40 transition-colors"
              aria-label="Attach blueprint image"
            >
              <ImagePlus size={18} />
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              capture="environment"
              onChange={handleFileChange}
              className="hidden"
              aria-label="Upload blueprint image"
            />
            <textarea
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={blueprintSummary ? 'Add details or send…' : 'Describe the plumbing job...'}
              aria-label="Type a pricing question"
              rows={1}
              disabled={isInputDisabled}
              className="input max-h-[120px] resize-none overflow-auto py-2.5 flex-1"
              style={{ minHeight: '46px' }}
            />
            {/* Mic button */}
            {speechSupported && !isInputDisabled && (
              <button
                type="button"
                onClick={() => {
                  haptic('tap')
                  onToggleSpeech()
                }}
                className={cn(
                  'flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border transition-colors',
                  speechListening
                    ? 'border-red-400 bg-red-100 text-red-600 animate-pulse'
                    : 'border-[color:var(--line)] bg-[color:var(--panel-strong)] text-[color:var(--muted-ink)] hover:text-[color:var(--ink)]'
                )}
                aria-label={speechListening ? 'Stop listening' : 'Voice input'}
                title={speechListening ? 'Listening…' : 'Tap to speak'}
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 19v3"/><path d="M12 2a3 3 0 0 1 3 3v7a3 3 0 0 1-6 0V5a3 3 0 0 1 3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><path d="M8 19h8"/></svg>
              </button>
            )}
            {disabled ? (
              <button
                type="button"
                onClick={() => {
                  haptic('warning')
                  onStopGenerating()
                }}
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
                  haptic('tap')
                  onSubmit()
                }}
                disabled={isInputDisabled || (!input.trim() && !blueprintSummary)}
                className="btn-primary h-11 w-11 shrink-0 rounded-2xl p-0 disabled:opacity-40"
                aria-label="Send message"
              >
                <Send size={16} />
              </button>
            )}
          </div>

          {/* Footer actions */}
          <div className="mt-1.5 flex items-center justify-between px-0.5">
            {messages.length > 0 ? (
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => {
                    haptic('tap')
                    onNewConversation()
                  }}
                  className="inline-flex items-center gap-1.5 text-[11px] text-[color:var(--muted-ink)] transition-colors hover:text-[color:var(--ink)] min-h-[44px] min-w-[44px]"
                >
                  <RotateCcw size={11} />
                  New conversation
                </button>
                <button
                  type="button"
                  onClick={() => {
                    haptic('tap')
                    onLoadSessions()
                    onSetSessionsOpen(true)
                  }}
                  className="inline-flex items-center gap-1.5 text-[11px] text-[color:var(--muted-ink)] transition-colors hover:text-[color:var(--ink)] min-h-[44px] min-w-[44px]"
                >
                  <History size={11} />
                  Past conversations
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-3">
                <span className="text-[11px] text-[color:var(--muted-ink)]">Enter to send · Shift+Enter for newline</span>
                <button
                  type="button"
                  onClick={() => {
                    haptic('tap')
                    onLoadSessions()
                    onSetSessionsOpen(true)
                  }}
                  className="inline-flex items-center gap-1.5 text-[11px] text-[color:var(--muted-ink)] transition-colors hover:text-[color:var(--ink)] min-h-[44px] min-w-[44px]"
                >
                  <History size={11} />
                  History
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Desktop side rail */}
      <aside className="hidden w-[360px] shrink-0 border-l border-[color:var(--line)] bg-[color:var(--panel)] lg:flex lg:flex-col">
        {/* Voice read-back toggle */}
        {ttsSupported && (
          <div className="flex items-center justify-between border-b border-[color:var(--line)] px-4 py-2">
            <span className="text-[11px] font-medium text-[color:var(--muted-ink)]">🔊 Read estimate aloud</span>
            <button
              type="button"
              onClick={() => {
                onToggleVoiceReadBack()
              }}
              className={cn(
                'relative h-5 w-9 rounded-full transition-colors',
                voiceReadBack ? 'bg-[color:var(--accent)]' : 'bg-[color:var(--line)]'
              )}
              aria-label="Toggle voice read-back"
            >
              <span className={cn(
                'absolute top-0.5 size-4 rounded-full bg-white transition-transform',
                voiceReadBack ? 'translate-x-4.5' : 'translate-x-0.5'
              )} />
            </button>
          </div>
        )}
        {selectedMessage?.estimate ? (
          <>
            <div className="flex-1 overflow-y-auto">
              <EstimateBreakdownV3
                estimate={selectedMessage.estimate}
                confidenceLabel={selectedMessage.confidence_label || 'HIGH'}
                confidenceScore={selectedMessage.confidence || 0.85}
                assumptions={selectedMessage.assumptions || []}
                county={county}
                marketAdjustments={selectedMessage.market_adjustments}
              />
            </div>
            {selectedMessage.estimate_id && (
              <EstimateVersionTimeline estimateId={selectedMessage.estimate_id} />
            )}
          </>
        ) : (
          <div className="flex flex-1 flex-col items-center justify-center px-6 text-center text-[color:var(--muted-ink)]">
            <DollarSign size={32} className="mb-3 opacity-30" />
            <p className="text-sm font-medium">No estimate selected</p>
            <p className="mt-1 text-xs opacity-60">Send a message to generate a priced estimate.</p>
          </div>
        )}
      </aside>

      {/* Sessions modal */}
      <Modal
        open={sessionsOpen}
        onClose={() => onSetSessionsOpen(false)}
        title="Past Conversations"
        size="md"
      >
        <div className="max-h-[60vh] overflow-y-auto">
          {sessions.length === 0 ? (
            <div className="py-8 text-center text-sm text-[color:var(--muted-ink)]">
              No past conversations yet.
            </div>
          ) : (
            <div className="space-y-2">
              {sessions.map(s => (
                <div
                  key={s.id}
                  role="button"
                  tabIndex={0}
                  className="group flex items-center gap-3 rounded-xl border border-[color:var(--line)] bg-[color:var(--panel-strong)] p-3 hover:bg-[color:var(--accent-soft)] transition-colors cursor-pointer"
                  onClick={() => onSelectSession(s.id, [], String(s.id))}
                  onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); (e.currentTarget as HTMLElement).click() } }}
                  aria-label={`Open conversation: ${s.title || 'Untitled'}`}
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-[color:var(--ink)] truncate">{s.title || 'Untitled conversation'}</p>
                    <p className="text-[11px] text-[color:var(--muted-ink)]">
                      {s.county}{s.county && s.job_type ? ' · ' : ''}{s.job_type} · {s.message_count} messages
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={async e => {
                      e.stopPropagation()
                      onDeleteSession(s.id)
                    }}
                    className="rounded-lg p-1.5 text-[color:var(--muted-ink)] opacity-0 group-hover:opacity-100 hover:bg-red-100 hover:text-red-600 transition-opacity"
                    aria-label="Delete session"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </Modal>

      {/* Image preview modal */}
      <Modal
        open={imagePreviewOpen}
        onClose={() => setImagePreviewOpen(false)}
        title="Image Preview"
        size="lg"
        className="sm:max-w-xl"
      >
        <div className="flex flex-col items-center gap-4">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={imagePreview || ''} alt="Preview" className="max-h-[60vh] w-full rounded-xl object-contain" />
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => {
                setImagePreviewOpen(false)
                onRemoveImage()
              }}
              className="rounded-xl border border-[color:var(--line)] bg-[color:var(--panel-strong)] px-4 py-2 text-sm font-medium text-[color:var(--muted-ink)] hover:bg-[color:var(--panel)] transition-colors"
            >
              Remove
            </button>
            <button
              type="button"
              onClick={() => {
                setImagePreviewOpen(false)
                onSubmit()
              }}
              disabled={isInputDisabled || (!input.trim() && !blueprintSummary)}
              className="btn-primary rounded-xl px-4 py-2 text-sm font-medium disabled:opacity-40"
            >
              Send
            </button>
          </div>
        </div>
      </Modal>

      {/* Mobile bottom sheet */}
      <AnimatePresence>
        {sheetOpen && selectedMessage?.estimate && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/40 lg:hidden"
            onClick={() => onSetSheetOpen(false)}
          >
            <motion.div
              initial={{ y: '100%' }}
              animate={{ y: 0 }}
              exit={{ y: '100%' }}
              transition={{ type: 'spring', stiffness: 350, damping: 35 }}
              className="absolute bottom-0 left-0 right-0 max-h-[85vh] overflow-hidden rounded-t-2xl bg-[color:var(--panel)] shadow-2xl"
              onClick={e => e.stopPropagation()}
            >
              {/* Drag handle */}
              <div className="flex justify-center pt-2 pb-1">
                <div className="h-1.5 w-10 rounded-full bg-[color:var(--line)]" />
              </div>
              <div className="flex items-center justify-between border-b border-[color:var(--line)] px-5 py-3">
                <span className="text-sm font-semibold text-[color:var(--ink)]">Estimate Breakdown</span>
                <button type="button" onClick={() => onSetSheetOpen(false)} className="rounded-lg p-1.5 hover:bg-[color:var(--panel-strong)]">
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

      {sessionId && (
        <ShareDialog
          sessionId={sessionId}
          open={shareOpen}
          onOpenChange={setShareOpen}
        />
      )}

      <TemplateEditor
        open={templateEditorOpen}
        onOpenChange={setTemplateEditorOpen}
      />
    </div>
  )
}
