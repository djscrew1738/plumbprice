'use client'

import {
  createContext,
  useContext,
  useRef,
  useCallback,
  useId,
  type ReactNode,
} from 'react'
import type { LucideIcon } from 'lucide-react'
import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'

/* ------------------------------------------------------------------ */
/*  Context                                                            */
/* ------------------------------------------------------------------ */

interface TabsCtx {
  value: string
  onChange: (value: string) => void
  baseId: string
}

const TabsContext = createContext<TabsCtx | null>(null)

function useTabs() {
  const ctx = useContext(TabsContext)
  if (!ctx) throw new Error('Tabs* components must be used within <TabsRoot>')
  return ctx
}

/* ------------------------------------------------------------------ */
/*  TabsRoot                                                           */
/* ------------------------------------------------------------------ */

export interface TabsRootProps {
  value: string
  onChange: (value: string) => void
  children: ReactNode
  className?: string
}

export function TabsRoot({ value, onChange, children, className }: TabsRootProps) {
  const baseId = useId()

  return (
    <TabsContext.Provider value={{ value, onChange, baseId }}>
      <div className={className}>{children}</div>
    </TabsContext.Provider>
  )
}

/* ------------------------------------------------------------------ */
/*  TabsList                                                           */
/* ------------------------------------------------------------------ */

export interface TabsListProps {
  children: ReactNode
  className?: string
}

export function TabsList({ children, className }: TabsListProps) {
  const listRef = useRef<HTMLDivElement>(null)

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (!listRef.current) return

    const tabs = Array.from(
      listRef.current.querySelectorAll<HTMLButtonElement>('[role="tab"]:not([disabled])'),
    )
    const currentIdx = tabs.findIndex(tab => tab === document.activeElement)

    let nextIdx: number | null = null

    switch (e.key) {
      case 'ArrowRight':
        e.preventDefault()
        nextIdx = (currentIdx + 1) % tabs.length
        break
      case 'ArrowLeft':
        e.preventDefault()
        nextIdx = (currentIdx - 1 + tabs.length) % tabs.length
        break
      case 'Home':
        e.preventDefault()
        nextIdx = 0
        break
      case 'End':
        e.preventDefault()
        nextIdx = tabs.length - 1
        break
    }

    if (nextIdx !== null) {
      tabs[nextIdx]?.focus()
      tabs[nextIdx]?.click()
    }
  }, [])

  return (
    <div
      ref={listRef}
      role="tablist"
      onKeyDown={handleKeyDown}
      className={cn(
        'relative flex border-b border-[color:var(--line)]',
        className,
      )}
    >
      {children}
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  TabsTrigger                                                        */
/* ------------------------------------------------------------------ */

export interface TabsTriggerProps {
  value: string
  children: ReactNode
  disabled?: boolean
  icon?: LucideIcon
  className?: string
}

export function TabsTrigger({
  value: tabValue,
  children,
  disabled = false,
  icon: Icon,
  className,
}: TabsTriggerProps) {
  const { value, onChange, baseId } = useTabs()
  const isActive = value === tabValue

  const tabId = `${baseId}-tab-${tabValue}`
  const panelId = `${baseId}-panel-${tabValue}`

  return (
    <button
      id={tabId}
      role="tab"
      type="button"
      aria-selected={isActive}
      aria-controls={panelId}
      tabIndex={isActive ? 0 : -1}
      disabled={disabled}
      onClick={() => onChange(tabValue)}
      className={cn(
        'relative inline-flex items-center gap-2 px-4 py-2.5 text-sm font-semibold transition-colors outline-none',
        'disabled:pointer-events-none disabled:opacity-40',
        isActive
          ? 'text-[color:var(--accent-strong)]'
          : 'text-[color:var(--muted-ink)] hover:text-[color:var(--ink)]',
        className,
      )}
    >
      {Icon && <Icon size={16} aria-hidden="true" />}
      {children}

      {/* Animated underline */}
      {isActive && (
        <motion.span
          layoutId={`${baseId}-indicator`}
          className="absolute bottom-0 left-0 right-0 h-0.5 bg-[color:var(--accent-strong)] rounded-full"
          transition={{ type: 'spring', stiffness: 500, damping: 35 }}
        />
      )}
    </button>
  )
}

/* ------------------------------------------------------------------ */
/*  TabsContent                                                        */
/* ------------------------------------------------------------------ */

export interface TabsContentProps {
  value: string
  children: ReactNode
  className?: string
}

export function TabsContent({
  value: tabValue,
  children,
  className,
}: TabsContentProps) {
  const { value, baseId } = useTabs()
  const isActive = value === tabValue

  const tabId = `${baseId}-tab-${tabValue}`
  const panelId = `${baseId}-panel-${tabValue}`

  if (!isActive) return null

  return (
    <div
      id={panelId}
      role="tabpanel"
      aria-labelledby={tabId}
      tabIndex={0}
      className={cn('outline-none', className)}
    >
      {children}
    </div>
  )
}
