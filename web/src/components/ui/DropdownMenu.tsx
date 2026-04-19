'use client'

import {
  createContext,
  useContext,
  useState,
  useRef,
  useCallback,
  useEffect,
  useId,
  type ReactNode,
} from 'react'
import type { LucideIcon } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '@/lib/utils'

/* ------------------------------------------------------------------ */
/*  Context                                                            */
/* ------------------------------------------------------------------ */

interface DropdownCtx {
  open: boolean
  setOpen: (v: boolean) => void
  triggerId: string
  menuId: string
  triggerRef: React.RefObject<HTMLButtonElement | null>
}

const DropdownContext = createContext<DropdownCtx | null>(null)

function useDropdown() {
  const ctx = useContext(DropdownContext)
  if (!ctx) throw new Error('Dropdown* components must be used within <DropdownMenu>')
  return ctx
}

/* ------------------------------------------------------------------ */
/*  DropdownMenu (root container)                                      */
/* ------------------------------------------------------------------ */

export interface DropdownMenuProps {
  children: ReactNode
  className?: string
}

export function DropdownMenu({ children, className }: DropdownMenuProps) {
  const [open, setOpen] = useState(false)
  const uid = useId()
  const triggerId = `${uid}-trigger`
  const menuId = `${uid}-menu`
  const triggerRef = useRef<HTMLButtonElement>(null)

  return (
    <DropdownContext.Provider value={{ open, setOpen, triggerId, menuId, triggerRef }}>
      <div className={cn('relative inline-block', className)}>
        {children}
      </div>
    </DropdownContext.Provider>
  )
}

/* ------------------------------------------------------------------ */
/*  DropdownTrigger                                                    */
/* ------------------------------------------------------------------ */

export interface DropdownTriggerProps {
  children: ReactNode
  className?: string
  'aria-label'?: string
}

export function DropdownTrigger({ children, className, 'aria-label': ariaLabel }: DropdownTriggerProps) {
  const { open, setOpen, triggerId, menuId, triggerRef } = useDropdown()

  return (
    <button
      ref={triggerRef}
      id={triggerId}
      type="button"
      aria-haspopup="true"
      aria-expanded={open}
      aria-controls={open ? menuId : undefined}
      aria-label={ariaLabel}
      onClick={() => setOpen(!open)}
      className={className}
    >
      {children}
    </button>
  )
}

/* ------------------------------------------------------------------ */
/*  DropdownContent                                                    */
/* ------------------------------------------------------------------ */

export interface DropdownContentProps {
  children: ReactNode
  align?: 'start' | 'end'
  className?: string
}

export function DropdownContent({
  children,
  align = 'end',
  className,
}: DropdownContentProps) {
  const { open, setOpen, triggerId, menuId, triggerRef } = useDropdown()
  const menuRef = useRef<HTMLDivElement>(null)
  const focusedIndex = useRef(-1)

  /* ---- close on click outside ---- */
  useEffect(() => {
    if (!open) return
    const handler = (e: MouseEvent) => {
      const target = e.target as Node
      if (
        menuRef.current &&
        !menuRef.current.contains(target) &&
        triggerRef.current &&
        !triggerRef.current.contains(target)
      ) {
        setOpen(false)
      }
    }
    window.addEventListener('mousedown', handler)
    return () => window.removeEventListener('mousedown', handler)
  }, [open, setOpen, triggerRef])

  /* ---- keyboard navigation ---- */
  useEffect(() => {
    if (!open) return

    const handler = (e: KeyboardEvent) => {
      if (!menuRef.current) return
      const items = Array.from(
        menuRef.current.querySelectorAll<HTMLElement>('[role="menuitem"]:not([aria-disabled="true"])'),
      )
      if (items.length === 0) return

      switch (e.key) {
        case 'ArrowDown': {
          e.preventDefault()
          focusedIndex.current = Math.min(focusedIndex.current + 1, items.length - 1)
          items[focusedIndex.current]?.focus()
          break
        }
        case 'ArrowUp': {
          e.preventDefault()
          focusedIndex.current = Math.max(focusedIndex.current - 1, 0)
          items[focusedIndex.current]?.focus()
          break
        }
        case 'Home': {
          e.preventDefault()
          focusedIndex.current = 0
          items[0]?.focus()
          break
        }
        case 'End': {
          e.preventDefault()
          focusedIndex.current = items.length - 1
          items[items.length - 1]?.focus()
          break
        }
        case 'Escape': {
          e.preventDefault()
          setOpen(false)
          triggerRef.current?.focus()
          break
        }
      }
    }

    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open, setOpen, triggerRef])

  // Reset focus index when menu closes
  useEffect(() => {
    if (!open) focusedIndex.current = -1
  }, [open])

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          ref={menuRef}
          id={menuId}
          role="menu"
          aria-labelledby={triggerId}
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          transition={{ duration: 0.12, ease: 'easeOut' }}
          className={cn(
            'absolute z-50 mt-1',
            align === 'end' ? 'right-0' : 'left-0',
            'border border-[color:var(--line)] bg-[color:var(--panel)] rounded-xl shadow-2xl py-1 min-w-[180px]',
            className,
          )}
        >
          {children}
        </motion.div>
      )}
    </AnimatePresence>
  )
}

/* ------------------------------------------------------------------ */
/*  DropdownItem                                                       */
/* ------------------------------------------------------------------ */

export interface DropdownItemProps {
  icon?: LucideIcon
  label: string
  onClick?: () => void
  disabled?: boolean
  destructive?: boolean
  className?: string
}

export function DropdownItem({
  icon: Icon,
  label,
  onClick,
  disabled = false,
  destructive = false,
  className,
}: DropdownItemProps) {
  const { setOpen } = useDropdown()

  const handleClick = useCallback(() => {
    if (disabled) return
    onClick?.()
    setOpen(false)
  }, [disabled, onClick, setOpen])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault()
        handleClick()
      }
    },
    [handleClick],
  )

  return (
    <div
      role="menuitem"
      tabIndex={disabled ? -1 : 0}
      aria-disabled={disabled || undefined}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      className={cn(
        'flex items-center gap-2.5 px-3 py-2 text-sm cursor-pointer transition-colors outline-none',
        destructive
          ? 'text-[hsl(var(--danger))] hover:bg-[hsl(var(--danger)/0.08)] focus-visible:bg-[hsl(var(--danger)/0.08)]'
          : 'text-[color:var(--ink)] hover:bg-[color:var(--panel-strong)] focus-visible:bg-[color:var(--panel-strong)]',
        disabled && 'opacity-40 pointer-events-none',
        className,
      )}
    >
      {Icon && <Icon size={16} className="shrink-0" aria-hidden="true" />}
      {label}
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  DropdownSeparator                                                  */
/* ------------------------------------------------------------------ */

export function DropdownSeparator() {
  return (
    <div
      role="separator"
      className="my-1 h-px bg-[color:var(--line)]"
    />
  )
}
