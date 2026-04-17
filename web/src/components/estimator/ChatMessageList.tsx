'use client'

import { motion } from 'framer-motion'
import { Copy, Check, Square } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ChatMessage } from '@/types'
import ReactMarkdown from 'react-markdown'
import { InlineEstimateCard } from './InlineEstimateCard'
import { ChatSkeleton } from '@/components/ui/Skeleton'

function formatTime(d: Date) {
  return d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true })
}

interface ChatMessageListProps {
  messages: ChatMessage[]
  loading: boolean
  copiedId: string | null
  onCopyMessage: (id: string, content: string) => void
  onViewBreakdown: (message: ChatMessage) => void
  onStopGenerating: () => void
}

export function ChatMessageList({
  messages,
  loading,
  copiedId,
  onCopyMessage,
  onViewBreakdown,
  onStopGenerating,
}: ChatMessageListProps) {
  return (
    <>
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

          <div className={cn('flex max-w-[85%] flex-col gap-1.5', message.role === 'user' ? 'items-end' : 'items-start')}>
            <div className={cn('relative px-4 py-3 text-sm leading-relaxed shadow-sm transition-all', message.role === 'user' ? 'chat-bubble-user' : 'chat-bubble-assistant')}>
              {message.role === 'assistant' ? (
                <>
                  <div className="chat-prose pr-4">
                    <ReactMarkdown>{message.content}</ReactMarkdown>
                  </div>
                  <button
                    type="button"
                    onClick={() => onCopyMessage(message.id, message.content)}
                    className="absolute right-2 top-2 rounded-lg p-2.5 min-w-[36px] min-h-[36px] text-[color:var(--muted-ink)] opacity-100 transition-all hover:bg-[color:var(--panel-strong)] lg:opacity-0 lg:group-hover:opacity-100"
                    title="Copy"
                    aria-label="Copy response"
                  >
                    {copiedId === message.id ? <Check size={13} className="text-[hsl(var(--success))]" /> : <Copy size={13} />}
                  </button>
                </>
              ) : (
                message.content
              )}

              {message.estimate && message.confidence_label && (
                <InlineEstimateCard
                  confidenceLabel={message.confidence_label}
                  confidenceScore={message.confidence || 0}
                  onViewBreakdown={() => onViewBreakdown(message)}
                />
              )}
            </div>

            <span className="text-[10px] font-medium text-[color:var(--muted-ink)] opacity-40 transition-opacity lg:opacity-0 lg:group-hover:opacity-100">
              {formatTime(message.timestamp)}
            </span>
          </div>
        </motion.div>
      ))}

      {loading && messages.length === 0 && (
        <ChatSkeleton />
      )}

      {loading && messages.length > 0 && (
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ type: 'spring', stiffness: 400, damping: 30 }} className="flex gap-3">
          <div className="flex size-8 shrink-0 items-center justify-center rounded-full border border-[color:var(--accent)]/20 bg-[color:var(--accent-soft)] text-[10px] font-bold text-[color:var(--accent-strong)] shadow-sm">
            AI
          </div>
          <div className="chat-bubble-assistant px-5 py-4">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1.5">
                <div className="typing-dot" />
                <div className="typing-dot" />
                <div className="typing-dot" />
              </div>
              <button
                type="button"
                onClick={onStopGenerating}
                className="ml-2 inline-flex items-center gap-1.5 rounded-full border border-[color:var(--line)] bg-[color:var(--panel)] px-2.5 py-1 text-[10px] font-bold text-[color:var(--muted-ink)] transition-colors hover:bg-[color:var(--panel-strong)] hover:text-[color:var(--ink)]"
              >
                <Square size={9} />
                Stop
              </button>
            </div>
          </div>
        </motion.div>
      )}
    </>
  )
}
