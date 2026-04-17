'use client'

import { motion } from 'framer-motion'
import { Send, RotateCcw, Square } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ChatInputBarProps {
  input: string
  loading: boolean
  uploadMode: boolean
  uploadedFile: File | null
  hasMessages: boolean
  maxInput: number
  onInputChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void
  onKeyDown: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void
  onSend: () => void
  onStopGenerating: () => void
  onReset: () => void
  inputRef: React.RefObject<HTMLTextAreaElement | null>
}

export function ChatInputBar({
  input,
  loading,
  uploadMode,
  uploadedFile,
  hasMessages,
  maxInput,
  onInputChange,
  onKeyDown,
  onSend,
  onStopGenerating,
  onReset,
  inputRef,
}: ChatInputBarProps) {
  return (
    <div className="border-t border-[color:var(--line)] bg-[color:var(--panel-strong)] px-3 pb-20 pt-2.5 lg:pb-3">
      <div className="flex items-end gap-2">
        <textarea
          ref={inputRef}
          value={input}
          onChange={onInputChange}
          onKeyDown={onKeyDown}
          placeholder={uploadMode && !uploadedFile ? 'Select a file above to begin…' : 'Ask a pricing question…'}
          aria-label="Type a pricing question"
          rows={1}
          maxLength={maxInput}
          disabled={uploadMode && !uploadedFile}
          className="input max-h-[120px] resize-none overflow-auto py-2.5 disabled:cursor-not-allowed disabled:opacity-65"
          style={{ minHeight: '46px' }}
        />
        {loading ? (
          <motion.button
            type="button"
            onClick={onStopGenerating}
            whileTap={{ scale: 0.9 }}
            className="btn-primary h-11 w-11 shrink-0 rounded-2xl bg-[hsl(var(--danger))] p-0 hover:bg-[hsl(var(--danger)/0.85)]"
            aria-label="Stop generating"
          >
            <Square size={14} />
          </motion.button>
        ) : (
          <motion.button
            type="button"
            onClick={onSend}
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
        ) : hasMessages ? (
          <button
            type="button"
            onClick={onReset}
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
            input.length >= maxInput ? 'text-[hsl(var(--danger))] font-semibold' : input.length > maxInput * 0.8 ? 'text-[hsl(var(--warning))]' : 'text-[color:var(--muted-ink)] opacity-60'
          )}>
            {input.length}/{maxInput}
          </span>
        )}
      </div>
    </div>
  )
}
