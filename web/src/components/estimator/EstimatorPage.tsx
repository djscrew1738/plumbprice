'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Send, RotateCcw, MapPin, ChevronDown, DollarSign, X,
  Zap, Copy, Check,
} from 'lucide-react'
import { chatApi } from '@/lib/api'
import { EstimateBreakdown } from './EstimateBreakdown'
import { ConfidenceBadge } from './ConfidenceBadge'
import { useToast } from '@/components/ui/Toast'
import { cn, formatCurrency } from '@/lib/utils'
import type { ChatMessage } from '@/types'
import ReactMarkdown from 'react-markdown'

const SUGGESTIONS = [
  { short: 'Toilet replace',   full: 'How much to replace a toilet first floor Dallas?',  hint: '$285–$485' },
  { short: 'WH attic 50G',    full: 'Price to replace 50G gas water heater in attic?',    hint: '$980–$1,400' },
  { short: 'Kitchen faucet',  full: 'Cost for kitchen faucet replacement?',                hint: '$180–$320' },
  { short: 'PRV valve',       full: 'Replace PRV valve -- how much?',                      hint: '$380–$580' },
  { short: 'Disposal install', full: 'Garbage disposal install cost?',                     hint: '$220–$380' },
  { short: 'Shower valve',    full: 'Replace shower valve and trim -- price?',             hint: '$420–$680' },
]

const COUNTIES = ['Dallas', 'Tarrant', 'Collin', 'Denton', 'Rockwall', 'Parker']

function formatTime(d: Date) {
  return d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true })
}

export function EstimatorPage() {
  const { success } = useToast()

  const [messages,         setMessages]         = useState<ChatMessage[]>([])
  const [input,            setInput]            = useState('')
  const [loading,          setLoading]          = useState(false)
  const [county,           setCounty]           = useState('Dallas')
  const [countyOpen,       setCountyOpen]       = useState(false)
  const [selectedEstimate, setSelectedEstimate] = useState<ChatMessage | null>(null)
  const [sheetOpen,        setSheetOpen]        = useState(false)
  const [copiedId,         setCopiedId]         = useState<string | null>(null)
  const [activeSuggestion, setActiveSuggestion] = useState(0)

  const bottomRef  = useRef<HTMLDivElement>(null)
  const inputRef   = useRef<HTMLTextAreaElement>(null)
  const countyRef  = useRef<HTMLDivElement>(null)

  // Scroll to latest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  // Rotate suggestion in empty state
  useEffect(() => {
    if (messages.length > 0) return
    const id = setInterval(() => setActiveSuggestion(p => (p + 1) % SUGGESTIONS.length), 3000)
    return () => clearInterval(id)
  }, [messages.length])

  // Close county dropdown on outside click
  useEffect(() => {
    const fn = (e: MouseEvent) => {
      if (countyRef.current && !countyRef.current.contains(e.target as Node)) setCountyOpen(false)
    }
    document.addEventListener('mousedown', fn)
    return () => document.removeEventListener('mousedown', fn)
  }, [])

  // Auto-grow textarea
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
    e.target.style.height = 'auto'
    e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px'
  }

  const copyMessage = (id: string, content: string) => {
    navigator.clipboard.writeText(content).then(() => {
      setCopiedId(id)
      success('Copied to clipboard')
      setTimeout(() => setCopiedId(null), 2000)
    })
  }

  const sendMessage = useCallback(async (text?: string) => {
    const msg = (text ?? input).trim()
    if (!msg || loading) return

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: msg,
      timestamp: new Date(),
    }

    setMessages(prev => [...prev, userMsg])
    setInput('')
    if (inputRef.current) inputRef.current.style.height = 'auto'
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
        content: 'Could not reach the API. Please check that the backend is running.',
        timestamp: new Date(),
      }])
    } finally {
      setLoading(false)
    }
  }, [input, loading, county])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage() }
  }

  const handleReset = () => {
    setMessages([])
    setSelectedEstimate(null)
    setSheetOpen(false)
    inputRef.current?.focus()
  }

  return (
    <div className="flex h-[calc(100dvh-54px)]">

      {/* ── Chat panel ── */}
      <div className="flex flex-col flex-1 min-w-0">

        {/* Top bar */}
        <div className="bg-[#080808]/90 backdrop-blur-xl border-b border-white/[0.06] px-3 py-2 flex items-center gap-2 shrink-0">
          {/* County dropdown */}
          <div ref={countyRef} className="relative shrink-0">
            <button
              onClick={() => setCountyOpen(o => !o)}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl bg-white/[0.05] border border-white/[0.08] hover:bg-white/[0.08] transition-colors"
            >
              <MapPin size={12} className="text-blue-400" />
              <span className="text-xs font-semibold text-zinc-300">{county} Co.</span>
              <ChevronDown size={11} className={cn('text-zinc-500 transition-transform duration-200', countyOpen && 'rotate-180')} />
            </button>
            <AnimatePresence>
              {countyOpen && (
                <motion.div
                  initial={{ opacity: 0, y: -6, scale: 0.96 }}
                  animate={{ opacity: 1, y: 0,  scale: 1    }}
                  exit={{   opacity: 0, y: -6,  scale: 0.96 }}
                  transition={{ duration: 0.12 }}
                  className="absolute top-full left-0 mt-1.5 bg-[#111] border border-white/[0.08] rounded-xl shadow-2xl overflow-hidden z-20 min-w-[148px]"
                >
                  {COUNTIES.map(c => (
                    <button
                      key={c}
                      onClick={() => { setCounty(c); setCountyOpen(false) }}
                      className={cn(
                        'w-full text-left px-3.5 py-2 text-xs font-medium transition-colors',
                        c === county ? 'text-blue-400 bg-blue-500/10' : 'text-zinc-400 hover:text-white hover:bg-white/[0.06]',
                      )}
                    >
                      {c} County
                    </button>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Suggestion pills */}
          <div className="flex items-center gap-1.5 overflow-x-auto scrollbar-hide flex-1">
            {SUGGESTIONS.map(s => (
              <button
                key={s.short}
                onClick={() => sendMessage(s.full)}
                disabled={loading}
                className="shrink-0 px-2.5 py-1.5 rounded-full bg-white/[0.04] hover:bg-blue-500/15 hover:text-blue-400 text-zinc-500 text-[11px] font-medium whitespace-nowrap border border-white/[0.06] hover:border-blue-500/20 transition-all disabled:opacity-30"
              >
                {s.short}
              </button>
            ))}
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-3 py-4 space-y-5 bg-[#080808]">

          {/* ── Empty state ── */}
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full pb-8 text-center px-4">
              <div className="w-14 h-14 rounded-2xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center mb-5">
                <Zap size={26} className="text-blue-400" />
              </div>

              <h2 className="text-2xl font-bold text-white mb-2 tracking-tight">DFW Plumbing Estimator</h2>
              <p className="text-zinc-500 text-sm max-w-[280px] mb-1 leading-relaxed">
                Real pricing with full labor, materials &amp; tax — every line item traceable.
              </p>

              {/* Animated current suggestion */}
              <div className="h-6 mb-8 overflow-hidden">
                <AnimatePresence mode="wait">
                  <motion.p
                    key={activeSuggestion}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{   opacity: 0, y: -8 }}
                    transition={{ duration: 0.3 }}
                    className="text-xs text-blue-400/70 font-medium"
                  >
                    Try: &ldquo;{SUGGESTIONS[activeSuggestion].full}&rdquo;
                  </motion.p>
                </AnimatePresence>
              </div>

              <div className="grid grid-cols-2 gap-2.5 w-full max-w-sm">
                {SUGGESTIONS.map((s, i) => (
                  <motion.button
                    key={s.short}
                    onClick={() => sendMessage(s.full)}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.2, delay: i * 0.05 }}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.97 }}
                    className="text-left px-3.5 py-3 rounded-2xl bg-[#0f0f0f] border border-white/[0.07] hover:border-blue-500/25 hover:bg-blue-500/[0.04] transition-all"
                  >
                    <div className="font-semibold text-zinc-200 text-xs mb-0.5">{s.short}</div>
                    <div className="text-[10px] text-zinc-600 leading-tight mb-1.5 line-clamp-1">{s.full}</div>
                    <div className="text-[11px] font-bold text-blue-400">{s.hint}</div>
                  </motion.button>
                ))}
              </div>
            </div>
          )}

          {/* ── Message list ── */}
          {messages.map((msg, i) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.18, delay: i > messages.length - 3 ? 0.04 : 0 }}
              className={cn('flex gap-2.5 group', msg.role === 'user' ? 'justify-end' : 'justify-start')}
            >
              {msg.role === 'assistant' && (
                <div className="w-[26px] h-[26px] rounded-full bg-blue-600/20 border border-blue-500/25 flex items-center justify-center text-blue-400 text-[9px] font-bold shrink-0 mt-1">
                  AI
                </div>
              )}

              <div className="flex flex-col gap-1 max-w-[88%]">
                <div className={cn(
                  'text-sm leading-relaxed relative',
                  msg.role === 'user' ? 'chat-bubble-user' : 'chat-bubble-assistant',
                )}>
                  {msg.role === 'assistant' ? (
                    <>
                      <div className="chat-prose pr-6">
                        <ReactMarkdown>{msg.content}</ReactMarkdown>
                      </div>
                      {/* Copy button */}
                      <button
                        onClick={() => copyMessage(msg.id, msg.content)}
                        className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 p-1 rounded-lg hover:bg-white/10 text-zinc-600 hover:text-zinc-300 transition-all"
                        title="Copy"
                      >
                        {copiedId === msg.id ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
                      </button>
                    </>
                  ) : msg.content}

                  {msg.estimate && msg.confidence_label && (
                    <div className="mt-2.5 pt-2.5 border-t border-white/[0.08] flex items-center justify-between gap-2">
                      <ConfidenceBadge label={msg.confidence_label} score={msg.confidence || 0} size="sm" />
                      <button
                        onClick={() => { setSelectedEstimate(msg); setSheetOpen(true) }}
                        className="text-xs font-semibold text-blue-400 hover:text-blue-300 transition-colors"
                      >
                        Breakdown →
                      </button>
                    </div>
                  )}
                </div>

                {/* Timestamp */}
                <span className={cn(
                  'text-[10px] text-zinc-700 opacity-0 group-hover:opacity-100 transition-opacity',
                  msg.role === 'user' ? 'text-right' : 'text-left',
                )}>
                  {formatTime(msg.timestamp)}
                </span>
              </div>

              {msg.role === 'user' && (
                <div className="w-[26px] h-[26px] rounded-full bg-zinc-800 flex items-center justify-center text-zinc-400 text-[9px] font-bold shrink-0 mt-1">
                  U
                </div>
              )}
            </motion.div>
          ))}

          {/* Typing */}
          {loading && (
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="flex gap-2.5">
              <div className="w-[26px] h-[26px] rounded-full bg-blue-600/20 border border-blue-500/25 flex items-center justify-center text-blue-400 text-[9px] font-bold shrink-0">
                AI
              </div>
              <div className="chat-bubble-assistant py-3.5 px-4">
                <div className="flex gap-1.5 items-center">
                  <div className="typing-dot" /><div className="typing-dot" /><div className="typing-dot" />
                </div>
              </div>
            </motion.div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* ── Input bar ── */}
        <div className="bg-[#080808]/90 backdrop-blur-xl border-t border-white/[0.06] px-3 pt-2.5 pb-20 lg:pb-3 shrink-0">
          <div className="flex gap-2 items-end">
            <textarea
              ref={inputRef}
              value={input}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              placeholder="Ask a pricing question…"
              rows={1}
              className="flex-1 resize-none px-4 py-3 border border-white/[0.08] rounded-2xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/25 focus:border-blue-500/40 max-h-[120px] overflow-auto bg-white/[0.04] text-white placeholder-zinc-600 transition-all leading-relaxed"
              style={{ minHeight: '46px' }}
            />
            <motion.button
              onClick={() => sendMessage()}
              disabled={!input.trim() || loading}
              whileTap={{ scale: 0.9 }}
              className="w-11 h-11 rounded-2xl bg-blue-600 text-white flex items-center justify-center hover:bg-blue-500 active:bg-blue-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors shrink-0"
            >
              <Send size={16} />
            </motion.button>
          </div>
          <div className="flex items-center justify-between mt-1.5 px-0.5">
            {messages.length > 0 ? (
              <button onClick={handleReset} className="flex items-center gap-1.5 text-[11px] text-zinc-600 hover:text-zinc-400 transition-colors">
                <RotateCcw size={11} /> New conversation
              </button>
            ) : (
              <span className="text-[11px] text-zinc-700">Enter to send · Shift+Enter for newline</span>
            )}
            {input.length > 0 && (
              <span className="text-[10px] text-zinc-700 tabular-nums">{input.length}</span>
            )}
          </div>
        </div>
      </div>

      {/* ── Desktop breakdown panel ── */}
      <div className="hidden lg:flex w-[380px] shrink-0 bg-[#0a0a0a] border-l border-white/[0.06] flex-col">
        {selectedEstimate?.estimate ? (
          <motion.div
            initial={{ opacity: 0, x: 16 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.25, ease: 'easeOut' }}
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
              <div className="w-12 h-12 bg-white/[0.03] border border-white/[0.06] rounded-2xl flex items-center justify-center mx-auto mb-4">
                <DollarSign size={20} className="text-zinc-700" />
              </div>
              <p className="text-sm font-medium text-zinc-600 mb-1">Estimate panel</p>
              <p className="text-xs text-zinc-700 max-w-[160px] mx-auto leading-relaxed">
                Ask a pricing question to see the full cost breakdown here.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* ── Mobile bottom sheet ── */}
      <AnimatePresence>
        {sheetOpen && selectedEstimate?.estimate && (
          <>
            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/70 backdrop-blur-sm z-40 lg:hidden"
              onClick={() => setSheetOpen(false)}
            />
            <motion.div
              initial={{ y: '100%' }} animate={{ y: 0 }} exit={{ y: '100%' }}
              transition={{ type: 'spring', damping: 28, stiffness: 320 }}
              className="fixed inset-x-0 bottom-0 z-50 lg:hidden"
              style={{ maxHeight: '87dvh' }}
            >
              <div
                className="bg-[#0f0f0f] rounded-t-3xl shadow-2xl flex flex-col overflow-hidden border-t border-white/[0.07]"
                style={{ maxHeight: '87dvh', paddingBottom: 'max(env(safe-area-inset-bottom), 16px)' }}
              >
                <div className="flex items-center justify-center pt-3 pb-1 shrink-0">
                  <div className="w-9 h-1 bg-white/15 rounded-full" />
                </div>
                <div className="flex items-center justify-between px-5 py-2.5 shrink-0 border-b border-white/[0.06]">
                  <span className="text-sm font-bold text-white">Estimate Breakdown</span>
                  <button onClick={() => setSheetOpen(false)} className="p-1.5 rounded-xl hover:bg-white/10 text-zinc-500 transition-colors">
                    <X size={17} />
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

      {/* ── Mobile FAB ── */}
      <AnimatePresence>
        {selectedEstimate?.estimate && !sheetOpen && (
          <motion.button
            initial={{ opacity: 0, y: 12, scale: 0.9 }}
            animate={{ opacity: 1, y: 0,  scale: 1    }}
            exit={{   opacity: 0, y: 12,  scale: 0.9  }}
            whileTap={{ scale: 0.94 }}
            onClick={() => setSheetOpen(true)}
            className="fixed bottom-[76px] right-4 z-30 lg:hidden flex items-center gap-2 bg-blue-600 text-white px-4 py-2.5 rounded-2xl shadow-xl shadow-blue-600/25 font-bold text-sm"
          >
            <DollarSign size={15} />
            {formatCurrency(selectedEstimate.estimate.grand_total)}
            <ChevronDown size={13} className="opacity-60" />
          </motion.button>
        )}
      </AnimatePresence>
    </div>
  )
}
