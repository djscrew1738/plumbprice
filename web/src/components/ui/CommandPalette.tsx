'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import {
  BriefcaseBusiness,
  Download,
  FileOutput,
  FileText,
  House,
  Layers,
  Moon,
  Package,
  Plus,
  Search,
  Settings,
  type LucideIcon,
} from 'lucide-react'
import { estimatesApi, type EstimateListItem } from '@/lib/api'

interface CommandItem {
  id: string
  label: string
  icon: LucideIcon
  shortcut?: string
  action: () => void
}

interface CommandSection {
  title: string
  items: CommandItem[]
}

export function CommandPalette() {
  const router = useRouter()
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [recentEstimates, setRecentEstimates] = useState<EstimateListItem[]>([])
  const inputRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLDivElement>(null)

  const close = useCallback(() => {
    setOpen(false)
    setQuery('')
    setSelectedIndex(0)
  }, [])

  // Listen for the custom event
  useEffect(() => {
    const handler = () => setOpen(true)
    window.addEventListener('show-command-palette', handler)
    return () => window.removeEventListener('show-command-palette', handler)
  }, [])

  // Fetch recent estimates when opening
  useEffect(() => {
    if (!open) return
    let cancelled = false
    estimatesApi.list({ limit: 5 }).then(res => {
      if (cancelled) return
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const data = res.data as any;
      setRecentEstimates('items' in data ? data.items : Array.isArray(data) ? data : [])
    }).catch(() => {
      // silently ignore
    })
    return () => { cancelled = true }
  }, [open])

  // Auto-focus input when opened
  useEffect(() => {
    if (open) {
      requestAnimationFrame(() => inputRef.current?.focus())
    }
  }, [open])

  const staticSections: CommandSection[] = useMemo(() => [
    {
      title: 'Navigation',
      items: [
        { id: 'nav-home', label: 'Home', icon: House, shortcut: 'G H', action: () => router.push('/') },
        { id: 'nav-estimates', label: 'Estimates', icon: FileText, shortcut: 'G E', action: () => router.push('/estimates') },
        { id: 'nav-pipeline', label: 'Pipeline', icon: BriefcaseBusiness, shortcut: 'G P', action: () => router.push('/pipeline') },
        { id: 'nav-proposals', label: 'Proposals', icon: FileOutput, shortcut: 'G R', action: () => router.push('/proposals') },
        { id: 'nav-blueprints', label: 'Blueprints', icon: Layers, shortcut: 'G B', action: () => router.push('/blueprints') },
        { id: 'nav-suppliers', label: 'Suppliers', icon: Package, shortcut: 'G S', action: () => router.push('/suppliers') },
        { id: 'nav-admin', label: 'Admin', icon: Settings, shortcut: 'G A', action: () => router.push('/admin') },
      ],
    },
    {
      title: 'Actions',
      items: [
        { id: 'act-new-estimate', label: 'New Estimate', icon: Plus, shortcut: 'N', action: () => router.push('/estimator') },
        { id: 'act-export-csv', label: 'Export Estimates (CSV)', icon: Download, action: () => router.push('/estimates?export=csv') },
        { id: 'act-dark-mode', label: 'Toggle Dark Mode', icon: Moon, action: () => { /* placeholder */ } },
      ],
    },
  ], [router])

  const sections: CommandSection[] = useMemo(() => {
    const lowerQuery = query.toLowerCase()

    const fuzzyMatch = (text: string) => {
      if (!lowerQuery) return true
      let qi = 0
      const lower = text.toLowerCase()
      for (let i = 0; i < lower.length && qi < lowerQuery.length; i++) {
        if (lower[i] === lowerQuery[qi]) qi++
      }
      return qi === lowerQuery.length
    }

    const filtered = staticSections
      .map(section => ({
        ...section,
        items: section.items.filter(item => fuzzyMatch(item.label)),
      }))
      .filter(section => section.items.length > 0)

    // Add recent estimates section
    if (recentEstimates.length > 0) {
      const recentItems: CommandItem[] = recentEstimates
        .filter(est => fuzzyMatch(est.title))
        .map(est => ({
          id: `recent-${est.id}`,
          label: est.title,
          icon: FileText,
          action: () => router.push(`/estimates/${est.id}`),
        }))

      if (recentItems.length > 0) {
        filtered.push({ title: 'Recent Estimates', items: recentItems })
      }
    }

    return filtered
  }, [query, staticSections, recentEstimates, router])

  // Flat list of all visible items for keyboard navigation
  const flatItems = useMemo(() => sections.flatMap(s => s.items), [sections])

  // Reset selected index when query changes
  useEffect(() => {
    setSelectedIndex(0)
  }, [query])

  // Scroll selected item into view
  useEffect(() => {
    if (!listRef.current) return
    const el = listRef.current.querySelector('[data-selected="true"]')
    el?.scrollIntoView({ block: 'nearest' })
  }, [selectedIndex])

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        setSelectedIndex(i => (i + 1) % Math.max(flatItems.length, 1))
        break
      case 'ArrowUp':
        e.preventDefault()
        setSelectedIndex(i => (i - 1 + flatItems.length) % Math.max(flatItems.length, 1))
        break
      case 'Enter':
        e.preventDefault()
        if (flatItems[selectedIndex]) {
          flatItems[selectedIndex].action()
          close()
        }
        break
      case 'Escape':
        e.preventDefault()
        e.stopPropagation()
        close()
        break
    }
  }, [flatItems, selectedIndex, close])

  let itemCounter = -1

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.12 }}
            className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
            onClick={close}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: -8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: -8 }}
            transition={{ duration: 0.15, ease: 'easeOut' }}
            className="fixed left-1/2 top-[18%] z-50 w-full max-w-lg -translate-x-1/2 overflow-hidden rounded-2xl border border-white/10 bg-zinc-900/95 shadow-2xl backdrop-blur-xl"
            role="dialog"
            aria-label="Command palette"
            onKeyDown={handleKeyDown}
          >
            {/* Search input */}
            <div className="flex items-center gap-3 border-b border-white/[0.06] px-4 py-3">
              <Search size={16} className="shrink-0 text-zinc-500" />
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={e => setQuery(e.target.value)}
                placeholder="Type a command..."
                className="w-full bg-transparent text-base text-zinc-300 placeholder:text-zinc-600 outline-none"
              />
              <kbd className="shrink-0 rounded bg-zinc-800 px-1.5 py-0.5 text-[10px] text-zinc-600">
                ESC
              </kbd>
            </div>

            {/* Results */}
            <div ref={listRef} className="max-h-[360px] overflow-y-auto overscroll-contain p-2">
              {sections.length === 0 && (
                <p className="px-3 py-6 text-center text-sm text-zinc-600">No results found</p>
              )}
              {sections.map(section => (
                <div key={section.title} className="mb-1">
                  <p className="px-3 pb-1.5 pt-2 text-[10px] font-bold uppercase tracking-widest text-zinc-600">
                    {section.title}
                  </p>
                  {section.items.map(item => {
                    itemCounter++
                    const isSelected = itemCounter === selectedIndex
                    const idx = itemCounter
                    const Icon = item.icon
                    return (
                      <button
                        key={item.id}
                        data-selected={isSelected}
                        onClick={() => { item.action(); close() }}
                        onMouseEnter={() => setSelectedIndex(idx)}
                        className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm transition-colors ${
                          isSelected ? 'bg-white/[0.08] text-white' : 'text-zinc-400 hover:bg-white/[0.05]'
                        }`}
                      >
                        <Icon size={15} className="shrink-0" />
                        <span className="flex-1 truncate">{item.label}</span>
                        {item.shortcut && (
                          <span className="shrink-0 rounded bg-zinc-800 px-1.5 py-0.5 text-[10px] text-zinc-600">
                            {item.shortcut}
                          </span>
                        )}
                      </button>
                    )
                  })}
                </div>
              ))}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
