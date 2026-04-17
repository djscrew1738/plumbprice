'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Bell,
  FileImage,
  FileText,
  DollarSign,
  Trophy,
  Info,
  X,
  CheckCheck,
} from 'lucide-react'
import { Tooltip } from '@/components/ui/Tooltip'
import {
  useNotifications,
  useUnreadCount,
  useMarkNotificationRead,
  useMarkAllRead,
  useDismissNotification,
} from '@/lib/hooks/useNotifications'
import type { NotificationType } from '@/lib/notifications'

// ─── Helpers ────────────────────────────────────────────────────────────────

const TYPE_ICONS: Record<NotificationType, typeof Bell> = {
  blueprint_complete: FileImage,
  proposal_viewed: FileText,
  price_alert: DollarSign,
  outcome_recorded: Trophy,
  system: Info,
}

const TYPE_COLORS: Record<NotificationType, string> = {
  blueprint_complete: 'text-blue-500',
  proposal_viewed: 'text-violet-500',
  price_alert: 'text-amber-500',
  outcome_recorded: 'text-emerald-500',
  system: 'text-[color:var(--muted-ink)]',
}

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60_000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  if (days < 7) return `${days}d ago`
  return new Date(iso).toLocaleDateString()
}

// ─── Component ──────────────────────────────────────────────────────────────

export function NotificationBell() {
  const router = useRouter()
  const [open, setOpen] = useState(false)
  const panelRef = useRef<HTMLDivElement>(null)

  const { data: notifications = [] } = useNotifications()
  const unreadCount = useUnreadCount()
  const markRead = useMarkNotificationRead()
  const markAllRead = useMarkAllRead()
  const dismiss = useDismissNotification()

  const recent = notifications.slice(0, 20)

  // Close on outside click
  useEffect(() => {
    if (!open) return
    const handler = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  // Close on Escape
  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [open])

  const handleClick = useCallback(
    (id: string, link?: string) => {
      markRead.mutate(id)
      if (link) {
        setOpen(false)
        router.push(link)
      }
    },
    [markRead, router],
  )

  const handleDismiss = useCallback(
    (e: React.MouseEvent, id: string) => {
      e.stopPropagation()
      dismiss.mutate(id)
    },
    [dismiss],
  )

  return (
    <div className="relative" ref={panelRef}>
      {/* Bell button */}
      <Tooltip content="Notifications">
        <button
          onClick={() => setOpen(prev => !prev)}
          aria-label={`Notifications${unreadCount > 0 ? ` (${unreadCount} unread)` : ''}`}
          aria-expanded={open}
          aria-haspopup="true"
          className="relative flex size-9 items-center justify-center rounded-full bg-[color:var(--panel)] text-[color:var(--muted-ink)] hover:bg-[color:var(--panel-strong)] hover:text-[color:var(--ink)] transition-colors"
        >
          <Bell size={16} />
          {unreadCount > 0 && (
            <span className="absolute -top-0.5 -right-0.5 flex items-center justify-center bg-[hsl(var(--danger))] text-white text-[10px] font-bold min-w-[18px] h-[18px] rounded-full px-1 pointer-events-none">
              {unreadCount > 99 ? '99+' : unreadCount}
            </span>
          )}
        </button>
      </Tooltip>

      {/* Dropdown panel */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -6, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.97 }}
            transition={{ type: 'spring', stiffness: 420, damping: 32 }}
            role="region"
            aria-label="Notifications"
            className="absolute right-0 top-full mt-2 w-[360px] max-w-[calc(100vw-2rem)] rounded-xl border border-[color:var(--line)] bg-[color:var(--panel)] shadow-2xl z-50 flex flex-col overflow-hidden"
          >
            {/* Header */}
            <div className="flex items-center justify-between border-b border-[color:var(--line)] px-4 py-3">
              <h2 className="text-sm font-bold text-[color:var(--ink)]">Notifications</h2>
              {unreadCount > 0 && (
                <button
                  onClick={() => markAllRead.mutate()}
                  className="flex items-center gap-1.5 text-[11px] font-semibold text-[color:var(--accent-strong)] hover:underline"
                >
                  <CheckCheck size={13} />
                  Mark all read
                </button>
              )}
            </div>

            {/* List */}
            <div className="max-h-[400px] overflow-y-auto overscroll-contain">
              {recent.length === 0 ? (
                <div className="flex flex-col items-center justify-center gap-2 py-12 text-[color:var(--muted-ink)]">
                  <Bell size={28} strokeWidth={1.5} aria-hidden="true" />
                  <p className="text-sm font-medium">No notifications</p>
                </div>
              ) : (
                recent.map(n => {
                  const Icon = TYPE_ICONS[n.type] ?? Info
                  const color = TYPE_COLORS[n.type] ?? 'text-[color:var(--muted-ink)]'
                  return (
                    <button
                      key={n.id}
                      onClick={() => handleClick(n.id, n.link)}
                      className={`group flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-[color:var(--panel-strong)] ${
                        !n.read ? 'bg-[color:var(--accent-soft)]' : ''
                      }`}
                    >
                      <span className={`mt-0.5 shrink-0 ${color}`} aria-hidden="true">
                        <Icon size={16} />
                      </span>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <p className="truncate text-sm font-semibold text-[color:var(--ink)]">
                            {n.title}
                          </p>
                          {!n.read && (
                            <span className="h-2 w-2 shrink-0 rounded-full bg-[hsl(var(--danger))]" aria-hidden="true" />
                          )}
                          {!n.read && (
                            <span className="sr-only">Unread</span>
                          )}
                        </div>
                        <p className="mt-0.5 line-clamp-2 text-xs text-[color:var(--muted-ink)]">
                          {n.message}
                        </p>
                        <p className="mt-1 text-[10px] text-[color:var(--muted-ink)] opacity-70">
                          {relativeTime(n.createdAt)}
                        </p>
                      </div>
                      <span
                        role="button"
                        tabIndex={0}
                        aria-label="Dismiss notification"
                        onClick={(e) => handleDismiss(e, n.id)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault()
                            handleDismiss(e as unknown as React.MouseEvent, n.id)
                          }
                        }}
                        className="mt-0.5 shrink-0 rounded-lg p-1 text-[color:var(--muted-ink)] opacity-0 transition-opacity group-hover:opacity-100 hover:text-[color:var(--ink)]"
                      >
                        <X size={13} />
                      </span>
                    </button>
                  )
                })
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
