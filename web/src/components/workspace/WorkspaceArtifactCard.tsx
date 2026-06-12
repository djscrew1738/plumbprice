'use client'

import { memo } from 'react'
import { motion } from 'framer-motion'
import { Copy, Check, RotateCcw, AlertCircle } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useReducedMotion } from '@/lib/useReducedMotion'
import type { ChatMessage } from '@/types'
import { ConfidenceBadge } from '@/components/ui/ConfidenceBadge'

interface WorkspaceArtifactCardProps {
  message: ChatMessage
  isCopied: boolean
  onCopy: (id: string, content: string) => void
  onRetry?: () => void
}

export const WorkspaceArtifactCard = memo(function WorkspaceArtifactCard({
  message,
  isCopied,
  onCopy,
  onRetry,
}: WorkspaceArtifactCardProps) {
  const reduce = useReducedMotion()
  const isUser = message.role === 'user'
  const isError = message.isError
  const hasEstimate = !!message.estimate

  return (
    <motion.div
      initial={reduce ? { opacity: 0.8 } : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, ease: 'easeOut' }}
      whileHover={reduce ? undefined : { y: -1 }}
      className={cn(
        'group relative flex gap-3',
        isUser ? 'flex-row-reverse' : 'flex-row'
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          'flex size-8 shrink-0 items-center justify-center rounded-full text-xs font-bold',
          isUser
            ? 'bg-[color:var(--accent)] text-white'
            : 'bg-[color:var(--accent-soft)] text-[color:var(--accent-strong)]'
        )}
      >
        {isUser ? 'You' : 'AI'}
      </div>

      {/* Content */}
      <div className={cn('min-w-0 max-w-[85%]', isUser ? 'items-end' : 'items-start')}>
        {/* Bubble */}
        <div
          className={cn(
            'relative rounded-[1.25rem] px-4 py-3',
            isUser
              ? 'rounded-tr-sm bg-[color:var(--accent)] text-white'
              : isError
                ? 'rounded-tl-sm border-l-4 border-l-[color:var(--danger)] bg-[color:var(--panel-solid)] text-[color:var(--ink)]'
                : hasEstimate
                  ? 'rounded-tl-sm border border-[color:var(--line)] bg-[color:var(--panel-solid)] text-[color:var(--ink)]'
                  : 'rounded-tl-sm border border-[color:var(--line)] bg-[color:var(--panel-solid)] text-[color:var(--ink)]'
          )}
        >
          {/* Error icon */}
          {isError && (
            <div className="mb-2 flex items-center gap-2 text-[color:var(--danger)]">
              <AlertCircle size={16} aria-hidden="true" />
              <span className="text-xs font-semibold">Something went wrong</span>
            </div>
          )}

          {/* Message content */}
          <div className="text-sm leading-relaxed whitespace-pre-wrap">
            {message.content || (message.role === 'assistant' && !isError ? (
              <span className="flex items-center gap-1">
                <span className="typing-dot" />
                <span className="typing-dot" />
                <span className="typing-dot" />
              </span>
            ) : null)}
          </div>

          {/* Estimate artifact inline */}
          {hasEstimate && !isError && (
            <div className="mt-3 border-t border-[color:var(--line)] pt-3">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-[color:var(--muted-ink)]">Estimated total</p>
                  <p className="text-2xl font-bold text-[color:var(--ink)]">
                    ${message.estimate!.grand_total.toLocaleString()}
                  </p>
                </div>
                {message.confidence_label && (
                  <ConfidenceBadge
                    label={message.confidence_label}
                    score={message.confidence ?? 0}
                    size="sm"
                  />
                )}
              </div>
            </div>
          )}
        </div>

        {/* Actions row */}
        <div className={cn(
          'mt-1 flex items-center gap-2 opacity-0 transition-opacity duration-fast group-hover:opacity-100',
          isUser && 'justify-end'
        )}>
          {!isUser && message.content && (
            <button
              onClick={() => onCopy(message.id, message.content)}
              className="flex items-center gap-1 rounded-lg px-2 py-1 text-[11px] font-medium text-[color:var(--muted-ink)] hover:bg-[color:var(--panel-strong)] hover:text-[color:var(--ink)] transition-colors"
              aria-label={isCopied ? 'Copied' : 'Copy message'}
            >
              {isCopied ? <Check size={12} /> : <Copy size={12} />}
              {isCopied ? 'Copied' : 'Copy'}
            </button>
          )}
          {isError && onRetry && (
            <button
              onClick={onRetry}
              className="flex items-center gap-1 rounded-lg px-2 py-1 text-[11px] font-medium text-[color:var(--danger)] hover:bg-[color:var(--danger-soft)] transition-colors"
            >
              <RotateCcw size={12} />
              Retry
            </button>
          )}
        </div>
      </div>
    </motion.div>
  )
})
