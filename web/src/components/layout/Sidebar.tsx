'use client'

import { usePathname } from 'next/navigation'
import Link from 'next/link'
import { AnimatePresence, motion } from 'framer-motion'
import {
  MessageSquare, FileText, Package, Layers, FileOutput,
  Settings, X, Droplets, BriefcaseBusiness, Lock,
} from 'lucide-react'
import { cn } from '@/lib/utils'

const CORE_NAV = [
  { href: '/pipeline',  icon: BriefcaseBusiness, label: 'Pipeline' },
  { href: '/estimator', icon: MessageSquare,      label: 'Estimator' },
  { href: '/estimates', icon: FileText,           label: 'Estimates' },
]

const TOOLS_NAV = [
  { href: '/suppliers', icon: Package,   label: 'Suppliers' },
  { href: '/admin',     icon: Settings,  label: 'Admin' },
]

const SOON_NAV = [
  { href: '/blueprints', icon: Layers,     label: 'Blueprints' },
  { href: '/proposals',  icon: FileOutput, label: 'Proposals' },
]

function NavItem({
  href, icon: Icon, label, onClick,
}: {
  href: string; icon: typeof MessageSquare; label: string; onClick?: () => void
}) {
  const pathname = usePathname()
  const active = pathname === href || pathname.startsWith(href + '/')

  return (
    <Link
      href={href}
      onClick={onClick}
      className={cn(
        'relative flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-150',
        active
          ? 'bg-blue-600/15 text-white'
          : 'text-zinc-500 hover:text-zinc-200 hover:bg-white/[0.05]',
      )}
    >
      {active && (
        <motion.div
          layoutId="navIndicator"
          className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-[22px] bg-blue-500 rounded-r-full"
          transition={{ type: 'spring', stiffness: 400, damping: 30 }}
        />
      )}
      <Icon
        size={17}
        strokeWidth={active ? 2.25 : 1.75}
        className={active ? 'text-blue-400' : ''}
      />
      {label}
    </Link>
  )
}

function SidebarContent({ onClose }: { onClose?: () => void }) {
  return (
    <div className="flex flex-col h-full">
      {/* Top accent line */}
      <div className="h-px bg-gradient-to-r from-transparent via-blue-500/40 to-transparent shrink-0" />

      {/* Logo */}
      <div className="flex items-center justify-between h-[60px] px-4 border-b border-white/[0.06] shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-[34px] h-[34px] bg-gradient-to-br from-blue-500 to-blue-700 rounded-xl flex items-center justify-center shadow-lg shadow-blue-600/25 shrink-0">
            <Droplets size={17} className="text-white" />
          </div>
          <div>
            <div className="text-[13px] font-bold text-white leading-none tracking-tight">PlumbPrice AI</div>
            <div className="text-[10px] text-blue-400/80 font-medium leading-none mt-1">DFW Estimator</div>
          </div>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="lg:hidden p-1.5 rounded-lg text-zinc-600 hover:text-white hover:bg-white/10 transition-colors"
          >
            <X size={16} />
          </button>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-2.5 pb-3 scrollbar-hide">
        <div className="nav-section-label">Workspace</div>
        <div className="space-y-0.5">
          {CORE_NAV.map(item => (
            <NavItem key={item.href} {...item} onClick={onClose} />
          ))}
        </div>

        <div className="nav-section-label">Tools</div>
        <div className="space-y-0.5">
          {TOOLS_NAV.map(item => (
            <NavItem key={item.href} {...item} onClick={onClose} />
          ))}
        </div>

        <div className="nav-section-label">Coming Soon</div>
        <div className="space-y-0.5">
          {SOON_NAV.map(({ href, icon: Icon, label }) => (
            <div
              key={href}
              className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-zinc-700 cursor-default select-none"
            >
              <Icon size={17} strokeWidth={1.5} />
              {label}
              <Lock size={11} className="ml-auto text-zinc-800" />
            </div>
          ))}
        </div>
      </nav>

      {/* Footer status */}
      <div className="px-4 py-3 border-t border-white/[0.06] shrink-0">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2 w-2 shrink-0">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-50" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
          </span>
          <span className="text-[11px] text-zinc-500 font-medium">DFW Market · Live</span>
          <span className="ml-auto text-[10px] text-zinc-700">v0.1</span>
        </div>
      </div>
    </div>
  )
}

export function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <>
      {/* Desktop sidebar */}
      <aside
        className="hidden lg:flex fixed inset-y-0 left-0 w-[var(--sidebar-width,248px)] bg-[#0a0a0a] border-r border-white/[0.06] z-40 flex-col"
        style={{ paddingTop: 'env(safe-area-inset-top)' }}
      >
        <SidebarContent />
      </aside>

      {/* Mobile sidebar */}
      <AnimatePresence>
        {open && (
          <motion.aside
            initial={{ x: '-100%' }}
            animate={{ x: 0 }}
            exit={{ x: '-100%' }}
            transition={{ type: 'spring', damping: 28, stiffness: 320 }}
            className="fixed inset-y-0 left-0 w-[var(--sidebar-width,248px)] bg-[#0a0a0a] border-r border-white/[0.06] z-40 flex flex-col lg:hidden"
            style={{ paddingTop: 'env(safe-area-inset-top)' }}
          >
            <SidebarContent onClose={onClose} />
          </motion.aside>
        )}
      </AnimatePresence>
    </>
  )
}
