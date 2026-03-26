'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, RotateCcw, MapPin, ChevronDown, DollarSign, X } from 'lucide-react'
import { chatApi, type ChatPriceResponse } from '@/lib/api'
import { EstimateBreakdown } from './EstimateBreakdown'
import { ConfidenceBadge } from './ConfidenceBadge'
import { cn, formatCurrency } from '@/lib/utils'
import type { ChatMessage } from '@/types'
import ReactMarkdown from 'react-markdown'

const SUGGESTIONS = [
  { short: 'Toilet replace', full: 'How much to replace a toilet first floor Dallas?' },
  { short: 'WH attic 50G', full: 'Price to replace 50G gas water heater in attic?' },
  { short: 'Kitchen faucet', full: 'Cost for kitchen faucet replacement?' },
  { short: 'PRV valve', full: 'Replace PRV valve -- how much?' },
  { short: 'Disposal install', full: 'Garbage disposal install cost?' },
  { short: 'Shower valve', full: 'Replace shower valve and trim -- price?' },
]

const COUNTIES = ['Dallas', 'Tarrant', 'Collin', 'Denton', 'Rockwall', 'Parker']

export function EstimatorPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [county, setCounty] = useState('Dallas')
  const [selectedEstimate, setSelectedEstimate] = useState<ChatMessage | null>(null)
  const [sheetOpen, setSheetOpen] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const sendMessage = useCallback(async (text?: string) => {
    const msg = text || input.trim()
    if (!msg || loading) return

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: msg,
      timestamp: new Date(),
    }

    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const { data } = await chatApi.price({ message: msg, county })

      const aiMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: data.answer,
        estimate: data.estimate,
        confidence: data.confidence,
        confidence_label: data.confidence_label,
        assumptions: data.assumptions,
        timestamp: new Date(),
      }

      setMessages(prev => [...prev, aiMsg])
      if (data.estimate) {
        setSelectedEstimate(aiMsg)
        setSheetOpen(true)
      }
    } catch {
      setMessages(prev => [...prev, {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: 'Sorry, there was an error. Please check that the API is running.',
        timestamp: new Date(),
      }])
    } finally {
      setLoading(false)
    }
  }, [input, loading, county])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const handleReset = () => {
    setMessages([])
    setSelectedEstimate(null)
    setSheetOpen(false)
  }

  return (
    <div className="flex h-[calc(100vh-56px)]">
      {/* Left: Chat panel */}
      <div className="flex flex-col flex-1 min-w-0">
        {/* Top bar: county selector + suggestion pills */}
        <div className="bg-black/40 backdrop-blur-xl border-b border-white/5 px-3 py-2.5 flex items-center gap-2 overflow-x-auto scrollbar-hide">
          <div className="flex items-center gap-1 shrink-0 bg-white/5 border border-white/10 rounded-xl px-2.5 py-1.5">
            <MapPin size={13} className="text-zinc-500" />
            <select
              value={county}
              onChange={e => setCounty(e.target.value)}
              className="text-xs font-semibold text-zinc-300 bg-transparent border-0 focus:outline-none cursor-pointer appearance-none pr-3"
            >
              {COUNTIES.map(c => <option key={c} value={c} className="bg-[#0f0f0f] text-zinc-300">{c} Co.</option>)}
            </select>
            <ChevronDown size={11} className="text-zinc-500 -ml-2 pointer-events-none" />
          </div>

          {SUGGESTIONS.map(s => (
            <button
              key={s.short}
              onClick={() => sendMessage(s.full)}
              disabled={loading}
              className="shrink-0 px-3 py-1.5 rounded-full bg-white/5 hover:bg-blue-500/20 hover:text-blue-400 text-zinc-400 text-xs font-medium whitespace-nowrap border border-white/5 transition-all disabled:opacity-40"
            >
              {s.short}
            </button>
          ))}
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-3 py-4 space-y-3 bg-[#0a0a0a]">
          {/* Empty state */}
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full pb-8 text-center px-4">
              <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-blue-600 rounded-2xl flex items-center justify-center mb-5 shadow-lg shadow-blue-500/20">
                <DollarSign size={32} className="text-white" />
              </div>
              <h2 className="text-xl font-bold text-white mb-2 tracking-tight">DFW Plumbing Estimator</h2>
              <p className="text-zinc-400 text-sm max-w-xs mb-8">
                Get deterministic pricing with full labor, materials &amp; tax breakdown -- every dollar traceable.
              </p>
              <div className="grid grid-cols-2 gap-2 w-full max-w-sm">
                {SUGGESTIONS.map(s => (
                  <motion.button
                    key={s.short}
                    onClick={() => sendMessage(s.full)}
                    whileHover={{ scale: 1.01 }}
                    whileTap={{ scale: 0.97 }}
                    className="text-left px-3.5 py-3 rounded-2xl glass-card text-sm text-zinc-400 hover:border-blue-500/30 hover:text-blue-400 transition-all"
                  >
                    <div className="font-semibold text-zinc-200 text-xs mb-0.5">{s.short}</div>
                    <div className="text-[11px] text-zinc-500 leading-tight">{s.full.substring(0, 40)}...</div>
                  </motion.button>
                ))}
              </div>
            </div>
          )}

          {/* Messages */}
          {messages.map((msg, i) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2, delay: i > messages.length - 3 ? 0.05 : 0 }}
              className={cn('flex gap-2.5', msg.role === 'user' ? 'justify-end' : 'justify-start')}
            >
              {msg.role === 'assistant' && (
                <div className="w-7 h-7 rounded-full bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center text-white text-[10px] font-bold shrink-0 mt-1">
                  AI
                </div>
              )}

              <div className={cn(
                'text-sm leading-relaxed',
                msg.role === 'user' ? 'chat-bubble-user' : 'chat-bubble-assistant'
              )}>
                {msg.role === 'assistant' ? (
                  <div className="chat-prose">
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  </div>
                ) : (
                  msg.content
                )}

                {msg.estimate && msg.confidence_label && (
                  <div className="mt-2.5 pt-2.5 border-t border-white/10 flex items-center justify-between gap-2">
                    <ConfidenceBadge label={msg.confidence_label} score={msg.confidence || 0} size="sm" />
                    <button
                      onClick={() => { setSelectedEstimate(msg); setSheetOpen(true) }}
                      className="text-xs font-semibold text-blue-400 hover:text-blue-300 flex items-center gap-1"
                    >
                      View breakdown -&gt;
                    </button>
                  </div>
                )}
              </div>

              {msg.role === 'user' && (
                <div className="w-7 h-7 rounded-full bg-white/10 flex items-center justify-center text-zinc-400 text-[10px] font-bold shrink-0 mt-1">
                  U
                </div>
              )}
            </motion.div>
          ))}

          {/* Typing indicator */}
          {loading && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex gap-2.5 justify-start"
            >
              <div className="w-7 h-7 rounded-full bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center text-white text-[10px] font-bold shrink-0">
                AI
              </div>
              <div className="chat-bubble-assistant py-3.5">
                <div className="flex gap-1 items-center">
                  <div className="typing-dot" />
                  <div className="typing-dot" />
                  <div className="typing-dot" />
                </div>
              </div>
            </motion.div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input bar */}
        <div className="bg-black/60 backdrop-blur-xl border-t border-white/5 px-3 py-3"
          style={{ paddingBottom: 'max(env(safe-area-inset-bottom), 12px)' }}>
          <div className="flex gap-2 items-end">
            <div className="flex-1 relative">
              <textarea
                ref={inputRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask a pricing question..."
                rows={1}
                className="w-full resize-none px-4 py-3 border border-white/10 rounded-2xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500/50 max-h-28 overflow-auto bg-white/5 text-white placeholder-zinc-500 transition-all"
                style={{ minHeight: '48px' }}
              />
            </div>
            <motion.button
              onClick={() => sendMessage()}
              disabled={!input.trim() || loading}
              whileTap={{ scale: 0.93 }}
              className="w-12 h-12 rounded-2xl bg-blue-600 text-white flex items-center justify-center hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors shrink-0"
            >
              <Send size={18} />
            </motion.button>
          </div>
          {messages.length > 0 && (
            <button
              onClick={handleReset}
              className="mt-2 flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
            >
              <RotateCcw size={12} />
              New conversation
            </button>
          )}
        </div>
      </div>

      {/* Right: Estimate panel (desktop only) */}
      <AnimatePresence>
        <div className="hidden lg:flex w-96 shrink-0 bg-black/30 border-l border-white/5 flex-col">
          {selectedEstimate?.estimate ? (
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3, ease: 'easeOut' }}
              className="flex-1 flex flex-col overflow-hidden"
            >
              <EstimateBreakdown
                estimate={selectedEstimate.estimate}
                confidenceLabel={selectedEstimate.confidence_label || 'HIGH'}
                confidenceScore={selectedEstimate.confidence || 0}
                assumptions={selectedEstimate.assumptions || []}
                county={county}
              />
            </motion.div>
          ) : (
            <div className="flex-1 flex items-center justify-center p-8 text-center">
              <div>
                <div className="w-14 h-14 bg-white/5 rounded-2xl flex items-center justify-center mx-auto mb-4 border border-white/[0.06]">
                  <DollarSign size={24} className="text-zinc-600" />
                </div>
                <h3 className="text-sm font-semibold text-zinc-400 mb-1.5">Estimate Panel</h3>
                <p className="text-xs text-zinc-600 max-w-[180px] mx-auto">
                  Ask a pricing question to see the full cost breakdown here.
                </p>
              </div>
            </div>
          )}
        </div>
      </AnimatePresence>

      {/* Mobile: Estimate bottom sheet */}
      <AnimatePresence>
        {sheetOpen && selectedEstimate?.estimate && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden"
              onClick={() => setSheetOpen(false)}
            />
            <motion.div
              initial={{ y: '100%' }}
              animate={{ y: 0 }}
              exit={{ y: '100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 300 }}
              className="fixed inset-x-0 bottom-0 z-50 lg:hidden"
              style={{ maxHeight: '85vh' }}
            >
              <div className="bg-[#0f0f0f] rounded-t-3xl shadow-2xl flex flex-col overflow-hidden border-t border-white/[0.06]"
                style={{
                  maxHeight: '85vh',
                  paddingBottom: 'max(env(safe-area-inset-bottom), 16px)'
                }}>
                <div className="flex items-center justify-between px-5 pt-4 pb-2 shrink-0">
                  <div className="w-10 h-1 bg-white/20 rounded-full mx-auto" />
                </div>
                <div className="flex items-center justify-between px-5 pb-3 shrink-0 border-b border-white/[0.06]">
                  <span className="text-base font-bold text-white">Estimate Breakdown</span>
                  <button
                    onClick={() => setSheetOpen(false)}
                    className="p-2 rounded-xl hover:bg-white/10 text-zinc-400"
                  >
                    <X size={18} />
                  </button>
                </div>
                <div className="flex-1 overflow-y-auto">
                  <EstimateBreakdown
                    estimate={selectedEstimate.estimate}
                    confidenceLabel={selectedEstimate.confidence_label || 'HIGH'}
                    confidenceScore={selectedEstimate.confidence || 0}
                    assumptions={selectedEstimate.assumptions || []}
                    county={county}
                    compact
                  />
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Mobile FAB */}
      <AnimatePresence>
        {selectedEstimate?.estimate && !sheetOpen && (
          <motion.button
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            whileTap={{ scale: 0.93 }}
            onClick={() => setSheetOpen(true)}
            className="fixed bottom-24 right-4 z-30 lg:hidden flex items-center gap-2 bg-blue-600 text-white px-4 py-3 rounded-2xl shadow-xl shadow-blue-600/30 font-bold text-sm"
          >
            <DollarSign size={16} />
            {formatCurrency(selectedEstimate.estimate.grand_total)}
            <ChevronDown size={14} className="opacity-70" />
          </motion.button>
        )}
      </AnimatePresence>
    </div>
  )
}
