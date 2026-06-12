'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import { chatApiV3 } from '@/lib/api-v3'
import { ChatMessageListV3, type ChatMessageV3 } from '@/components/estimator-v3/ChatMessageListV3'
import { EstimateBreakdownV3 } from '@/components/estimator-v3/EstimateBreakdownV3'
import { DollarSign } from 'lucide-react'

export default function SharePage() {
  const params = useParams()
  const token = params.token as string
  const [messages, setMessages] = useState<ChatMessageV3[]>([])
  const [selectedMessage, setSelectedMessage] = useState<ChatMessageV3 | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!token) return
    chatApiV3.getSharedSession(token)
      .then(res => {
        const loaded = res.data.session.messages.map(m => ({
          id: `share-${m.id}`,
          role: m.role as 'user' | 'assistant',
          content: m.content,
          timestamp: m.created_at ? new Date(m.created_at) : new Date(),
          estimate_id: m.estimate_id,
        }))
        setMessages(loaded)
        // Pre-select the last message with an estimate
        const lastWithEstimate = loaded.slice().reverse().find(m => m.estimate_id)
        if (lastWithEstimate) {
          setSelectedMessage(lastWithEstimate)
        }
        setLoading(false)
      })
      .catch(err => {
        setError(err.response?.data?.detail || 'Failed to load shared session')
        setLoading(false)
      })
  }, [token])

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-sm text-[color:var(--muted-ink)]">Loading shared conversation…</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center">
          <p className="text-sm font-medium text-[color:var(--ink)]">{error}</p>
          <p className="mt-1 text-xs text-[color:var(--muted-ink)]">This link may have expired or been revoked.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="border-b border-[color:var(--line)] bg-[color:var(--panel-strong)] px-4 py-3">
          <p className="text-xs text-[color:var(--muted-ink)]">🔒 Shared conversation — view only</p>
        </div>
        <div className="flex-1 overflow-y-auto px-4 py-6 md:px-8">
          <ChatMessageListV3
            messages={messages}
            loading={false}
            copiedId={null}
            onCopyMessage={() => {}}
            onViewBreakdown={setSelectedMessage}
            onStopGenerating={() => {}}
          />
        </div>
      </div>

      <aside className="hidden w-[360px] shrink-0 border-l border-[color:var(--line)] bg-[color:var(--panel)] lg:flex lg:flex-col">
        {selectedMessage?.estimate ? (
          <div className="flex-1 overflow-y-auto">
            <EstimateBreakdownV3
              estimate={selectedMessage.estimate}
              confidenceLabel={selectedMessage.confidence_label || 'HIGH'}
              confidenceScore={selectedMessage.confidence || 0.85}
              assumptions={selectedMessage.assumptions || []}
              county="Dallas"
              marketAdjustments={selectedMessage.market_adjustments}
            />
          </div>
        ) : (
          <div className="flex flex-1 flex-col items-center justify-center px-6 text-center text-[color:var(--muted-ink)]">
            <DollarSign size={32} className="mb-3 opacity-30" />
            <p className="text-sm font-medium">No estimate selected</p>
          </div>
        )}
      </aside>
    </div>
  )
}
