'use client'

import { motion } from 'framer-motion'
import { Copy, Check, MessageSquare } from 'lucide-react'
import { cn } from '@/lib/utils'
import { ChatSkeleton } from '@/components/ui/Skeleton'

import dynamic from 'next/dynamic'

const SafeMarkdown = dynamic(() => import('@/components/ui/SafeMarkdown').then(m => ({ default: m.SafeMarkdown })), { ssr: false })
import { ToolCallBubble } from './ToolCallBubble'
import { ReasoningBubble } from './ReasoningBubble'

function formatTime(d: Date) {
  return d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true })
}

export interface ChatMessageV3 {
  id: string
  role: 'user' | 'assistant'
  content: string
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
  confidence?: number
  confidence_label?: string
  assumptions?: string[]
  reasoning?: string
  tool_calls?: Array<{ tool_name: string; latency_ms: number; error?: string | null }>
  market_adjustments?: Array<{ name: string; category: string; factor: number }>
  timestamp?: Date
}

interface ChatMessageListV3Props {
  messages: ChatMessageV3[]
  loading: boolean
  copiedId: string | null
  onCopyMessage: (id: string, content: string) => void
  onViewBreakdown: (message: ChatMessageV3) => void
  onStopGenerating: () => void
}

export function ChatMessageListV3({
  messages,
  loading,
  copiedId,
  onCopyMessage,
  onViewBreakdown,
  onStopGenerating,
}: ChatMessageListV3Props) {
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
              <span key={hint} className="px-3 py-1.5 rounded-full bg-[color:var(--panel-strong)] border border-[color:var(--line)] text-xs text-[color:var(--muted-ink)] font-medium">
                {hint}
              </span>
            ))}
          </div>
        </div>
      )}
      {messages.map((message, index) => (
        <motion.div
          key={message.id}
          initial={{ opacity: 0, y: 12, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ type: 'spring', stiffness: 400, damping: 30, delay: index > messages.length - 3 ? 0.04 : 0 }}
          className={cn('mb-6 flex gap-3 group', message.role === 'user' ? 'flex-row-reverse' : 'justify-start')}
        >
          <div className={cn(
            'mt-1 flex size-8 shrink-0 items-center justify-center rounded-full text-[10px] font-bold shadow-sm',
            message.role === 'assistant'
              ? 'border border-[color:var(--accent)]/20 bg-[color:var(--accent-soft)] text-[color:var(--accent-strong)]'
              : 'bg-[color:var(--panel-strong)] text-[color:var(--muted-ink)]'
          )}>
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
                    <span className="text-[10px] text-[color:var(--muted-ink)]">
                      {message.confidence_label} · {Math.round((message.confidence || 0.85) * 100)}%
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => onViewBreakdown(message)}
                    className="w-full rounded-lg bg-[color:var(--accent)] px-3 py-1.5 text-xs font-semibold text-white hover:opacity-90 transition-opacity"
                  >
                    View Full Breakdown
                  </button>
                </div>
              )}

              {/* Timestamp + actions */}
              <div className={cn('mt-2 flex items-center gap-2', message.role === 'user' ? 'justify-end' : 'justify-start')}>
                <span className="text-[10px] opacity-50">
                  {message.timestamp ? formatTime(message.timestamp) : ''}
                </span>
                {message.role === 'assistant' && message.content && (
                  <button
                    type="button"
                    onClick={() => onCopyMessage(message.id, message.content)}
                    className="rounded p-1 text-[color:var(--muted-ink)] opacity-0 transition-opacity hover:bg-[color:var(--panel-strong)] group-hover:opacity-100"
                    aria-label="Copy message"
                    title="Copy"
                  >
                    {copiedId === message.id ? <Check size={12} className="text-emerald-500" /> : <Copy size={12} />}
                  </button>
                )}
              </div>
            </div>
          </div>
        </motion.div>
      ))}

      {loading && (
        <div className="mb-6 flex gap-3">
          <div className="mt-1 flex size-8 shrink-0 items-center justify-center rounded-full border border-[color:var(--accent)]/20 bg-[color:var(--accent-soft)] text-[10px] font-bold text-[color:var(--accent-strong)]">
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
