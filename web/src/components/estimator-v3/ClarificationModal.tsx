'use client'

import { motion, AnimatePresence } from 'framer-motion'
import { HelpCircle, Send } from 'lucide-react'
import { useState } from 'react'
import { cn } from '@/lib/utils'

interface ClarificationModalProps {
  questions: string[]
  onAnswer: (answer: string) => void
  onDismiss: () => void
}

export function ClarificationModal({ questions, onAnswer, onDismiss }: ClarificationModalProps) {
  const [selected, setSelected] = useState<string | null>(null)
  const [custom, setCustom] = useState('')

  const handleSubmit = () => {
    const answer = selected || custom
    if (answer.trim()) {
      onAnswer(answer.trim())
    }
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: 20 }}
        className="mb-4 rounded-xl border border-[color:var(--accent)]/20 bg-[color:var(--accent-soft)] p-4"
      >
        <div className="flex items-center gap-2 mb-3">
          <HelpCircle size={18} className="text-[color:var(--accent-strong)]" />
          <h3 className="text-sm font-semibold text-[color:var(--ink)]">
            Quick clarification needed
          </h3>
        </div>
        <p className="text-xs text-[color:var(--muted-ink)] mb-3">
          To give you the most accurate price, could you clarify:
        </p>
        <div className="space-y-2 mb-3">
          {questions.map((q, i) => (
            <button
              key={i}
              onClick={() => { setSelected(q); setCustom('') }}
              className={cn(
                'w-full text-left rounded-lg border px-3 py-2 text-xs transition-colors',
                selected === q
                  ? 'border-[color:var(--accent)] bg-white'
                  : 'border-[color:var(--line)] bg-[color:var(--panel)] hover:bg-[color:var(--panel-strong)]'
              )}
            >
              {q}
            </button>
          ))}
        </div>
        <textarea
          value={custom}
          onChange={e => { setCustom(e.target.value); setSelected(null) }}
          placeholder="Or describe in your own words..."
          className="w-full rounded-lg border border-[color:var(--line)] bg-[color:var(--panel)] px-3 py-2 text-xs text-[color:var(--ink)] placeholder:text-[color:var(--muted-ink)] mb-3 resize-none"
          rows={2}
        />
        <div className="flex gap-2">
          <button
            onClick={handleSubmit}
            disabled={!selected && !custom.trim()}
            className="inline-flex items-center gap-1.5 rounded-lg bg-[color:var(--accent)] px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-40"
          >
            <Send size={12} />
            Submit
          </button>
          <button
            onClick={onDismiss}
            className="rounded-lg border border-[color:var(--line)] px-3 py-1.5 text-xs font-medium text-[color:var(--muted-ink)] hover:bg-[color:var(--panel-strong)]"
          >
            Skip
          </button>
        </div>
      </motion.div>
    </AnimatePresence>
  )
}
