'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Lightbulb, ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ReasoningBubbleProps {
  content: string
}

export function ReasoningBubble({ content }: ReasoningBubbleProps) {
  const [open, setOpen] = useState(false)

  return (
    <div className="mb-2">
      <button
        onClick={() => setOpen(!open)}
        className={cn(
          'flex items-center gap-2 rounded-lg border px-3 py-2 text-xs transition-colors',
          'border-amber-200 bg-amber-50 text-amber-800 hover:bg-amber-100'
        )}
      >
        <Lightbulb size={14} className="text-amber-600 shrink-0" />
        <span className="font-medium">AI Reasoning</span>
        <ChevronDown
          size={14}
          className={cn('ml-auto transition-transform', open && 'rotate-180')}
        />
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="mt-1 rounded-lg border border-amber-100 bg-amber-50/50 px-3 py-2 text-xs text-amber-900 leading-relaxed">
              {content}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
