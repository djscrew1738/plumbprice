'use client'

import { memo } from 'react'
import { motion } from 'framer-motion'
import { Copy, Check, MessageSquare, ThumbsUp, ThumbsDown, AlertTriangle, Pencil, RotateCcw, Trash2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { ChatSkeleton } from '@/components/ui/Skeleton'
import { haptic } from '@/lib/haptics'
import { useReducedMotion } from '@/lib/useReducedMotion'
import { useSwipeActions } from './hooks/useSwipeActions'

import dynamic from 'next/dynamic'

const SafeMarkdown = dynamic(() => import('@/components/ui/SafeMarkdown').then(m => ({ default: m.SafeMarkdown })), { ssr: false })
import { ToolCallBubble } from './ToolCallBubble'
import { ReasoningBubble } from './ReasoningBubble'
import { IntakeCard } from './IntakeCard'
import type { IntakeResultV3, RevisionSuggestionV3 } from '@/lib/api-v3'

function formatTime(d: Date) {
  return d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true })
}

export interface EstimateDiffV3 {
  previous_total: number
  new_total: number
  total_delta: number
  added_line_items: Array<Record<string, unknown>>
  removed_line_items: Array<Record<string, unknown>>
  modified_line_items: Array<Record<string, unknown>>
}

export interface ChatMessageV3 {
  id: string
  role: 'user' | 'assistant'
  content: string
  estimate_id?: number | null
  estimate?: {
    grand_total: number
    labor_total: number
    materials_total: number
    tax_total: number
    markup_total: number
    misc_total: number
    subtotal: number
    line_items: Array<{
      line_type: string
      description: string
      quantity: number
      unit: string
      unit_cost: number
      total_cost: number
      supplier?: string | null
    }>
    market_adjustment_applied: number
  } | null
  estimate_diff?: EstimateDiffV3 | null
  confidence?: number
  confidence_label?: string
  assumptions?: string[]
  reasoning?: string
  tool_calls?: Array<{ tool_name: string; latency_ms: number; error?: string | null }>
  market_adjustments?: Array<{ name: string; category: string; factor: number }>
  blueprint_seeded?: boolean
  intake_result?: IntakeResultV3 | null
  revision_suggestions?: RevisionSuggestionV3[]
  intake_confirmed?: boolean
  template_used?: string | null
  timestamp?: Date
}

interface ChatMessageListV3Props {
  messages: ChatMessageV3[]
  loading: boolean
  copiedId: string | null
  onCopyMessage: (id: string, content: string) => void
  onViewBreakdown: (message: ChatMessageV3) => void
  onStopGenerating: () => void
  onFeedback?: (estimateId: number, vote: 'up' | 'down') => void
  feedbackState?: Record<number, 'up' | 'down'>
  estimateRecommendations?: Record<number, Array<{ id: number; source: string; rationale: string | null }>>
  // Sprint 2: message actions
  onEditMessage?: (id: string, content: string) => void
  onRegenerateMessage?: (id: string) => void
  onDeleteMessage?: (id: string) => void
  // Streaming state for stop/regenerate UI
  streamingMessageId?: string | null
  onRefine?: (prompt: string) => void
  // v6.6.0 intake + proactive suggestions
  onConfirmIntake?: (intake: IntakeResultV3) => void
  onSuggestionClick?: (suggestion: RevisionSuggestionV3) => void
}

interface MessageItemProps {
  message: ChatMessageV3
  index: number
  totalMessages: number
  reduceMotion: boolean
  copiedId: string | null
  onCopyMessage: (id: string, content: string) => void
  onViewBreakdown: (message: ChatMessageV3) => void
  onFeedback?: (estimateId: number, vote: 'up' | 'down') => void
  feedbackState: Record<number, 'up' | 'down'>
  estimateRecommendations: Record<number, Array<{ id: number; source: string; rationale: string | null }>>
  onEditMessage?: (id: string, content: string) => void
  onRegenerateMessage?: (id: string) => void
  onDeleteMessage?: (id: string) => void
  lastUserMessageId?: string
  streamingMessageId?: string | null
  onRefine?: (prompt: string) => void
  onStopGenerating: () => void
  onConfirmIntake?: (intake: IntakeResultV3) => void
  onSuggestionClick?: (suggestion: RevisionSuggestionV3) => void
}

const MessageItem = memo(function MessageItem({
  message,
  index,
  totalMessages,
  reduceMotion,
  copiedId,
  onCopyMessage,
  onViewBreakdown,
  onFeedback,
  feedbackState,
  estimateRecommendations,
  onEditMessage,
  onRegenerateMessage,
  onDeleteMessage,
  lastUserMessageId,
  streamingMessageId,
  onRefine,
  onStopGenerating,
  onConfirmIntake,
  onSuggestionClick,
}: MessageItemProps) {
  const swipe = useSwipeActions({
    onSwipeLeft: () => onDeleteMessage?.(message.id),
    onSwipeRight: () => {
      if (message.role === 'user') {
        onEditMessage?.(message.id, message.content)
      } else if (message.id === lastUserMessageId) {
        onRegenerateMessage?.(message.id)
      }
    },
  })

  const isStreaming = streamingMessageId === message.id

  return (
    <motion.div
      key={message.id}
      initial={reduceMotion ? { opacity: 0.9 } : { opacity: 0, y: 12, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={reduceMotion
        ? { duration: 0.1 }
        : { type: 'spring', stiffness: 400, damping: 30, delay: index > totalMessages - 3 ? 0.04 : 0 }
      }
      className={cn('mb-6 flex gap-3 group', message.role === 'user' ? 'flex-row-reverse' : 'justify-start')}
      style={swipe.swipe.deltaX !== 0 ? { transform: `translateX(${swipe.swipe.deltaX}px)` } : undefined}
      {...swipe.handlers}
    >
      <div
        className={cn(
          'mt-1 flex size-8 shrink-0 items-center justify-center rounded-full text-[10px] font-bold shadow-sm',
          message.role === 'assistant'
            ? 'border border-[color:var(--accent)]/20 bg-[color:var(--accent-soft)] text-[color:var(--accent-strong)]'
            : 'bg-[color:var(--panel-strong)] text-[color:var(--muted-ink)]'
        )}
        aria-label={message.role === 'assistant' ? 'Assistant' : 'You'}
      >
        {message.role === 'assistant' ? 'AI' : 'U'}
      </div>

      <div className={cn('max-w-[85%] md:max-w-[75%]', message.role === 'user' ? 'items-end' : 'items-start')}>
        {/* Reasoning bubble (v3) */}
        {message.role === 'assistant' && message.reasoning && (
          <ReasoningBubble content={message.reasoning} />
        )}

        {/* Tool call bubbles (v3) */}
        {message.role === 'assistant' && message.tool_calls && message.tool_calls.length > 0 && (
          <div className="mb-2 space-y-1">
            {message.tool_calls.map((tc, i) => (
              <ToolCallBubble
                key={i}
                tool={tc.tool_name}
                latencyMs={tc.latency_ms}
                error={tc.error}
              />
            ))}
          </div>
        )}

        {/* Intake card (v6.6.0) */}
        {message.role === 'assistant' && message.intake_result && !message.intake_confirmed && onConfirmIntake && (
          <IntakeCard
            intake={message.intake_result}
            onConfirm={onConfirmIntake}
          />
        )}

        {/* Message bubble */}
        <div className={cn(
          'relative rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm',
          message.role === 'assistant'
            ? 'bg-[color:var(--panel)] border border-[color:var(--line)] text-[color:var(--ink)]'
            : 'bg-[color:var(--accent)] text-white'
        )}>
          {message.role === 'assistant' ? (
            <div className="prose prose-sm dark:prose-invert max-w-none">
              <SafeMarkdown>{message.content || ''}</SafeMarkdown>
            </div>
          ) : (
            <p>{message.content}</p>
          )}

          {/* Inline estimate card */}
          {message.estimate && message.role === 'assistant' && (
            <div className="mt-3 rounded-xl border border-[color:var(--line)] bg-[color:var(--panel-strong)] p-3">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-[color:var(--ink)]">
                  {formatCurrency(message.estimate.grand_total)}
                </span>
                <div className="flex items-center gap-1.5">
                  {message.estimate_id && estimateRecommendations[message.estimate_id]?.length > 0 && (
                    <span className="inline-flex items-center gap-0.5 rounded-full bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">
                      <AlertTriangle size={10} />
                      Review
                    </span>
                  )}
                  {message.blueprint_seeded && (
                    <span className="inline-flex items-center gap-0.5 rounded-full bg-sky-100 px-1.5 py-0.5 text-[10px] font-semibold text-sky-700 dark:bg-sky-900/30 dark:text-sky-300" title="Quantities seeded from blueprint analysis">
                      🏗️ Blueprint
                    </span>
                  )}
                  <span className="text-[10px] text-[color:var(--muted-ink)]">
                    {message.confidence_label} · {Math.round((message.confidence || 0.85) * 100)}%
                  </span>
                </div>
              </div>
              {message.estimate_diff && (
                <div className="mb-2 flex flex-wrap gap-1.5">
                  <span className={cn(
                    'inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold',
                    (message.estimate_diff.total_delta || 0) >= 0
                      ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300'
                      : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300'
                  )}>
                    {(message.estimate_diff.total_delta || 0) >= 0 ? '▲' : '▼'} {formatCurrency(Math.abs(message.estimate_diff.total_delta || 0))}
                  </span>
                  {(message.estimate_diff.added_line_items?.length || 0) > 0 && (
                    <span className="inline-flex items-center rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-semibold text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
                      +{message.estimate_diff.added_line_items?.length} items
                    </span>
                  )}
                  {(message.estimate_diff.removed_line_items?.length || 0) > 0 && (
                    <span className="inline-flex items-center rounded-full bg-red-100 px-2 py-0.5 text-[10px] font-semibold text-red-700 dark:bg-red-900/30 dark:text-red-300">
                      −{message.estimate_diff.removed_line_items?.length} items
                    </span>
                  )}
                  {(message.estimate_diff.modified_line_items?.length || 0) > 0 && (
                    <span className="inline-flex items-center rounded-full bg-violet-100 px-2 py-0.5 text-[10px] font-semibold text-violet-700 dark:bg-violet-900/30 dark:text-violet-300">
                      ~{message.estimate_diff.modified_line_items?.length} changed
                    </span>
                  )}
                </div>
              )}
              <button
                type="button"
                onClick={() => {
                  haptic('tap')
                  onViewBreakdown(message)
                }}
                className="w-full rounded-lg bg-[color:var(--accent)] px-3 py-2 text-xs font-semibold text-white hover:opacity-90 transition-opacity min-h-[44px]"
              >
                View Full Breakdown
              </button>
              {message.estimate_id && onFeedback && (
                <div className="mt-2 flex items-center justify-center gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      haptic('tap')
                      onFeedback(message.estimate_id!, 'up')
                    }}
                    className={cn(
                      'flex items-center gap-1 rounded-lg px-2 py-1 text-[10px] font-medium transition-colors min-h-[32px]',
                      feedbackState[message.estimate_id] === 'up'
                        ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300'
                        : 'text-[color:var(--muted-ink)] hover:bg-[color:var(--panel-strong)]'
                    )}
                    aria-label="Thumbs up"
                    title="Accurate estimate"
                  >
                    <ThumbsUp size={12} />
                    {feedbackState[message.estimate_id] === 'up' ? 'Helpful' : 'Good'}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      haptic('tap')
                      onFeedback(message.estimate_id!, 'down')
                    }}
                    className={cn(
                      'flex items-center gap-1 rounded-lg px-2 py-1 text-[10px] font-medium transition-colors min-h-[32px]',
                      feedbackState[message.estimate_id] === 'down'
                        ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300'
                        : 'text-[color:var(--muted-ink)] hover:bg-[color:var(--panel-strong)]'
                    )}
                    aria-label="Thumbs down"
                    title="Inaccurate estimate"
                  >
                    <ThumbsDown size={12} />
                    {feedbackState[message.estimate_id] === 'down' ? 'Reported' : 'Off'}
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Proactive revision suggestions (v6.6.0) */}
          {message.role === 'assistant' && message.revision_suggestions && message.revision_suggestions.length > 0 && onSuggestionClick && (
            <div className="mt-2 flex flex-wrap gap-2">
              {message.revision_suggestions.map(suggestion => (
                <button
                  key={suggestion.id}
                  type="button"
                  onClick={() => {
                    haptic('tap')
                    onSuggestionClick(suggestion)
                  }}
                  className="rounded-full border border-[color:var(--line)] bg-[color:var(--panel-strong)] px-3 py-1.5 text-[11px] font-medium text-[color:var(--accent-strong)] hover:bg-[color:var(--accent-soft)] transition-colors"
                >
                  {suggestion.label}
                </button>
              ))}
            </div>
          )}

          {/* Timestamp + actions */}
          <div className={cn('mt-2 flex items-center gap-1', message.role === 'user' ? 'justify-end' : 'justify-start')}>
            <span className="text-[10px] opacity-50">
              {message.timestamp ? formatTime(message.timestamp) : ''}
            </span>

            {/* Message action buttons */}
            <div className="flex items-center gap-0.5">
              {/* Edit — only for user messages */}
              {message.role === 'user' && onEditMessage && (
                <button
                  type="button"
                  onClick={() => {
                    haptic('tap')
                    onEditMessage(message.id, message.content)
                  }}
                  className="rounded p-1 text-[color:var(--muted-ink)] opacity-100 transition-opacity hover:bg-[color:var(--panel-strong)] lg:opacity-0 lg:group-hover:opacity-100 min-h-[44px] min-w-[44px] flex items-center justify-center"
                  aria-label="Edit message"
                  title="Edit"
                >
                  <Pencil size={12} />
                </button>
              )}

              {/* Regenerate — only for assistant messages */}
              {message.role === 'assistant' && onRegenerateMessage && message.id === lastUserMessageId && (
                <button
                  type="button"
                  onClick={() => {
                    haptic('tap')
                    onRegenerateMessage(message.id)
                  }}
                  className="rounded p-1 text-[color:var(--muted-ink)] opacity-100 transition-opacity hover:bg-[color:var(--panel-strong)] lg:opacity-0 lg:group-hover:opacity-100 min-h-[44px] min-w-[44px] flex items-center justify-center"
                  aria-label="Regenerate response"
                  title="Regenerate"
                >
                  <RotateCcw size={12} />
                </button>
              )}

              {/* Copy — only for assistant messages with content */}
              {message.role === 'assistant' && message.content && (
                <button
                  type="button"
                  onClick={() => {
                    haptic('tap')
                    onCopyMessage(message.id, message.content)
                  }}
                  className="rounded p-1 text-[color:var(--muted-ink)] opacity-100 transition-opacity hover:bg-[color:var(--panel-strong)] lg:opacity-0 lg:group-hover:opacity-100 min-h-[44px] min-w-[44px] flex items-center justify-center"
                  aria-label="Copy message"
                  title="Copy"
                >
                  {copiedId === message.id ? <Check size={12} className="text-emerald-500" /> : <Copy size={12} />}
                </button>
              )}

              {/* Delete — for both roles */}
              {onDeleteMessage && (
                <button
                  type="button"
                  onClick={() => {
                    haptic('tap')
                    onDeleteMessage(message.id)
                  }}
                  className="rounded p-1 text-[color:var(--muted-ink)] opacity-100 transition-opacity hover:bg-red-100 hover:text-red-600 lg:opacity-0 lg:group-hover:opacity-100 min-h-[44px] min-w-[44px] flex items-center justify-center"
                  aria-label="Delete message"
                  title="Delete"
                >
                  <Trash2 size={12} />
                </button>
              )}
            </div>
          </div>

          {/* Streaming stop + refine chips */}
          {isStreaming && (
            <div className="mt-2">
              <button
                type="button"
                onClick={() => {
                  haptic('warning')
                  onStopGenerating()
                }}
                className="rounded-lg border border-[color:var(--line)] bg-[color:var(--panel-strong)] px-3 py-1.5 text-xs font-medium text-[color:var(--muted-ink)] hover:bg-[color:var(--panel)] transition-colors"
              >
                Stop generating
              </button>
            </div>
          )}

          {/* Refinement chips (shown after streaming stopped but message is incomplete) */}
          {isStreaming && !message.content.includes('[Error:') && onRefine && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              <span className="text-[10px] text-[color:var(--muted-ink)]">Try:</span>
              {['Regenerate', 'Make it cheaper', 'Add more detail'].map(label => (
                <button
                  key={label}
                  type="button"
                  onClick={() => {
                    haptic('tap')
                    const promptMap: Record<string, string> = {
                      'Regenerate': 'Try again with the same request.',
                      'Make it cheaper': 'Can you find a more budget-friendly option?',
                      'Add more detail': 'Please provide a more detailed breakdown.',
                    }
                    onRefine(promptMap[label])
                  }}
                  className="rounded-full border border-[color:var(--line)] bg-[color:var(--panel-strong)] px-2 py-1 text-[10px] font-medium text-[color:var(--muted-ink)] hover:bg-[color:var(--accent-soft)] hover:text-[color:var(--accent-strong)] transition-colors"
                >
                  {label}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </motion.div>
  )
})

export function ChatMessageListV3({
  messages,
  loading,
  copiedId,
  onCopyMessage,
  onViewBreakdown,
  onStopGenerating,
  onFeedback,
  feedbackState = {},
  estimateRecommendations = {},
  onEditMessage,
  onRegenerateMessage,
  onDeleteMessage,
  streamingMessageId,
  onRefine,
  onConfirmIntake,
  onSuggestionClick,
}: ChatMessageListV3Props) {
  const reduceMotion = useReducedMotion()
  const lastUserMessageId = messages.filter(m => m.role === 'user').pop()?.id

  return (
    <>
      {messages.length === 0 && !loading && (
        <div className="flex flex-col items-center justify-center py-16 px-6 gap-4 text-center select-none">
          <div className="flex size-14 items-center justify-center rounded-2xl bg-[color:var(--accent-soft)] border border-[color:var(--accent)]/20">
            <MessageSquare size={24} className="text-[color:var(--accent-strong)]" />
          </div>
          <div>
            <p className="text-base font-semibold text-[color:var(--ink)]">Start a conversation</p>
            <p className="mt-1 text-sm text-[color:var(--muted-ink)] max-w-xs">
              Describe the plumbing job and the AI will generate a detailed price estimate with real-time market data.
            </p>
          </div>
          <div className="flex flex-wrap gap-2 justify-center mt-1">
            {['Kitchen sink rough-in, 2 fixtures', 'Water heater replacement', '3-bed house repipe'].map(hint => (
              <span key={hint} className="px-3 py-1.5 rounded-full bg-[color:var(--panel-strong)] border border-[color:var(--line)] text-xs text-[color:var(--muted-ink)] font-medium min-h-[44px] min-w-[44px] flex items-center justify-center">
                {hint}
              </span>
            ))}
          </div>
        </div>
      )}
      {messages.map((message, index) => (
        <MessageItem
          key={message.id}
          message={message}
          index={index}
          totalMessages={messages.length}
          reduceMotion={reduceMotion}
          copiedId={copiedId}
          onCopyMessage={onCopyMessage}
          onViewBreakdown={onViewBreakdown}
          onFeedback={onFeedback}
          feedbackState={feedbackState}
          estimateRecommendations={estimateRecommendations}
          onEditMessage={onEditMessage}
          onRegenerateMessage={onRegenerateMessage}
          onDeleteMessage={onDeleteMessage}
          lastUserMessageId={lastUserMessageId}
          streamingMessageId={streamingMessageId}
          onRefine={onRefine}
          onStopGenerating={onStopGenerating}
          onConfirmIntake={onConfirmIntake}
          onSuggestionClick={onSuggestionClick}
        />
      ))}

      {/* Global loading skeleton (when no streaming message is tracked yet) */}
      {loading && !streamingMessageId && (
        <div className="mb-6 flex gap-3">
          <div
            className="mt-1 flex size-8 shrink-0 items-center justify-center rounded-full border border-[color:var(--accent)]/20 bg-[color:var(--accent-soft)] text-[10px] font-bold text-[color:var(--accent-strong)]"
            aria-label="Assistant"
          >
            AI
          </div>
          <div className="max-w-[75%]">
            <ChatSkeleton />
            <button
              type="button"
              onClick={onStopGenerating}
              className="mt-2 rounded-lg border border-[color:var(--line)] bg-[color:var(--panel-strong)] px-3 py-1.5 text-xs font-medium text-[color:var(--muted-ink)] hover:bg-[color:var(--panel)] transition-colors"
            >
              Stop generating
            </button>
          </div>
        </div>
      )}
    </>
  )
}

function formatCurrency(n: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n)
}
