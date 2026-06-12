'use client'

import { useState } from 'react'
import * as Dialog from '@radix-ui/react-dialog'
import { X, Link2, Copy, Check } from 'lucide-react'
import { cn } from '@/lib/utils'
import { chatApiV3 } from '@/lib/api-v3'
import { haptic } from '@/lib/haptics'

interface ShareDialogProps {
  sessionId: number
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function ShareDialog({ sessionId, open, onOpenChange }: ShareDialogProps) {
  const [expiryDays, setExpiryDays] = useState<number | null>(7)
  const [permission, setPermission] = useState<'read' | 'comment'>('read')
  const [shareUrl, setShareUrl] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [loading, setLoading] = useState(false)

  const handleCreate = async () => {
    setLoading(true)
    try {
      const res = await chatApiV3.createShare(sessionId, {
        permission,
        expires_in_days: expiryDays,
      })
      setShareUrl(`${window.location.origin}${res.data.url}`)
      haptic('success')
    } catch {
      haptic('error')
    } finally {
      setLoading(false)
    }
  }

  const handleCopy = () => {
    if (!shareUrl) return
    navigator.clipboard.writeText(shareUrl)
    setCopied(true)
    haptic('tap')
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <Dialog.Root open={open} onOpenChange={(o) => { if (!o) setShareUrl(null); onOpenChange(o) }}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm" />
        <Dialog.Content className="fixed left-1/2 top-[20%] z-50 w-full max-w-sm -translate-x-1/2 rounded-2xl border border-[color:var(--line)] bg-[color:var(--panel)] p-5 shadow-2xl focus:outline-none">
          <div className="mb-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Link2 size={15} className="text-[color:var(--accent-strong)]" />
              <h2 className="text-sm font-semibold text-[color:var(--ink)]">Share Conversation</h2>
            </div>
            <Dialog.Close asChild>
              <button aria-label="Close" className="rounded-lg p-2 text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] transition-colors">
                <X size={15} />
              </button>
            </Dialog.Close>
          </div>

          {!shareUrl ? (
            <div className="space-y-4">
              <div>
                <span className="mb-1.5 block text-[11px] font-medium uppercase tracking-wider text-[color:var(--muted-ink)]">Permission</span>
                <div className="flex gap-2">
                  {(['read', 'comment'] as const).map(p => (
                    <button
                      key={p}
                      type="button"
                      onClick={() => setPermission(p)}
                      className={cn(
                        'flex-1 rounded-lg border px-3 py-2 text-xs font-medium transition-colors',
                        permission === p
                          ? 'border-[color:var(--accent)] bg-[color:var(--accent-soft)] text-[color:var(--accent-strong)]'
                          : 'border-[color:var(--line)] bg-[color:var(--panel-strong)] text-[color:var(--muted-ink)] hover:bg-[color:var(--accent-soft)]'
                      )}
                    >
                      {p === 'read' ? '👁️ View only' : '💬 Can comment'}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <span className="mb-1.5 block text-[11px] font-medium uppercase tracking-wider text-[color:var(--muted-ink)]">Expires in</span>
                <div className="flex flex-wrap gap-2">
                  {[
                    { label: '1 day', value: 1 },
                    { label: '7 days', value: 7 },
                    { label: '30 days', value: 30 },
                    { label: 'Never', value: null },
                  ].map(opt => (
                    <button
                      key={opt.label}
                      type="button"
                      onClick={() => setExpiryDays(opt.value)}
                      className={cn(
                        'rounded-full border px-3 py-1.5 text-[11px] font-medium transition-colors',
                        expiryDays === opt.value
                          ? 'border-[color:var(--accent)] bg-[color:var(--accent-soft)] text-[color:var(--accent-strong)]'
                          : 'border-[color:var(--line)] bg-[color:var(--panel-strong)] text-[color:var(--muted-ink)] hover:bg-[color:var(--accent-soft)]'
                      )}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>

              <button
                type="button"
                onClick={handleCreate}
                disabled={loading}
                className="w-full rounded-xl bg-[color:var(--accent)] px-4 py-2.5 text-sm font-semibold text-white hover:opacity-90 transition-opacity disabled:opacity-40"
              >
                {loading ? 'Creating link…' : 'Create share link'}
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="rounded-lg border border-[color:var(--line)] bg-[color:var(--panel-strong)] p-3">
                <p className="mb-1 text-[10px] font-medium uppercase tracking-wider text-[color:var(--muted-ink)]">Share link</p>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    readOnly
                    value={shareUrl}
                    className="flex-1 rounded-md border border-[color:var(--line)] bg-[color:var(--panel)] px-2 py-1.5 text-xs text-[color:var(--ink)]"
                  />
                  <button
                    type="button"
                    onClick={handleCopy}
                    className="rounded-md bg-[color:var(--accent)] px-3 py-1.5 text-xs font-medium text-white hover:opacity-90 transition-opacity"
                  >
                    {copied ? <Check size={14} /> : <Copy size={14} />}
                  </button>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setShareUrl(null)}
                className="w-full rounded-xl border border-[color:var(--line)] bg-[color:var(--panel-strong)] px-4 py-2 text-xs font-medium text-[color:var(--muted-ink)] hover:bg-[color:var(--panel)] transition-colors"
              >
                Create another link
              </button>
            </div>
          )}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
