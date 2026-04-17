'use client'

import { motion, AnimatePresence } from 'framer-motion'
import { Zap } from 'lucide-react'

export interface Suggestion {
  short: string
  full: string
  hint: string
}

interface SuggestionGridProps {
  suggestions: Suggestion[]
  activeSuggestion: number
  onSelect: (fullText: string) => void
}

export function SuggestionGrid({ suggestions, activeSuggestion, onSelect }: SuggestionGridProps) {
  return (
    <div className="flex h-full flex-col items-center justify-center px-4 pb-8 text-center">
      <div className="mb-5 flex size-16 items-center justify-center rounded-2xl bg-gradient-to-br from-[color:var(--accent-soft)] to-[color:var(--accent)]/10 text-[color:var(--accent-strong)] shadow-sm">
        <Zap size={32} />
      </div>

      <h2 className="text-2xl font-bold tracking-tight text-[color:var(--ink)]">Quick Quote</h2>
      <p className="mt-2 max-w-[320px] text-sm leading-relaxed text-[color:var(--muted-ink)]">
        Describe the plumbing job in natural language. I&apos;ll generate a detailed estimate with local DFW pricing.
      </p>

      <div className="mb-8 mt-4 h-6 overflow-hidden">
        <AnimatePresence mode="wait">
          <motion.p
            key={activeSuggestion}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.3 }}
            className="text-xs font-bold text-[color:var(--accent-strong)]"
          >
            Try: &ldquo;{suggestions[activeSuggestion].full}&rdquo;
          </motion.p>
        </AnimatePresence>
      </div>

      <div className="grid w-full max-w-sm grid-cols-2 gap-3">
        {suggestions.map((suggestion, index) => (
          <motion.button
            key={suggestion.short}
            type="button"
            onClick={() => onSelect(suggestion.full)}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2, delay: index * 0.05 }}
            whileHover={{ scale: 1.02, backgroundColor: 'var(--panel-strong)' }}
            whileTap={{ scale: 0.97 }}
            className="flex flex-col rounded-2xl border border-[color:var(--line)] bg-[color:var(--panel)] p-3.5 text-left transition-colors"
          >
            <div className="text-xs font-bold text-[color:var(--ink)]">{suggestion.short}</div>
            <div className="mt-1 line-clamp-1 text-[10px] leading-tight text-[color:var(--muted-ink)]">{suggestion.full}</div>
            <div className="mt-2 text-[11px] font-extrabold text-[color:var(--accent-strong)]">{suggestion.hint}</div>
          </motion.button>
        ))}
      </div>
    </div>
  )
}
