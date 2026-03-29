'use client'

import { usePathname } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import { Menu, MessageSquare, FileText, Package, Layers, FileOutput, Settings, BriefcaseBusiness } from 'lucide-react'

const pages: Record<string, { title: string; icon: typeof MessageSquare }> = {
  '/':          { title: 'Chat Estimator',   icon: MessageSquare },
  '/estimator': { title: 'Chat Estimator',   icon: MessageSquare },
  '/pipeline':  { title: 'Revenue Pipeline', icon: BriefcaseBusiness },
  '/estimates': { title: 'Estimates',        icon: FileText },
  '/suppliers': { title: 'Suppliers',        icon: Package },
  '/blueprints':{ title: 'Blueprints',       icon: Layers },
  '/proposals': { title: 'Proposals',        icon: FileOutput },
  '/admin':     { title: 'Admin',            icon: Settings },
}

export function Header({ onMenuClick }: { onMenuClick: () => void }) {
  const pathname = usePathname()
  const page = pages[pathname] ?? { title: 'Chat Estimator', icon: MessageSquare }
  const PageIcon = page.icon

  return (
    <header
      className="bg-[#080808]/80 backdrop-blur-xl border-b border-white/[0.06] sticky top-0 z-20"
      style={{ paddingTop: 'env(safe-area-inset-top)' }}
    >
      <div className="flex items-center h-[54px] px-4 gap-3">
        {/* Hamburger — mobile only */}
        <button
          onClick={onMenuClick}
          className="lg:hidden p-2 -ml-1.5 rounded-lg text-zinc-500 hover:text-white hover:bg-white/10 transition-colors"
          aria-label="Open menu"
        >
          <Menu size={20} />
        </button>

        {/* Page title */}
        <div className="flex-1 flex items-center gap-2 min-w-0">
          <PageIcon size={15} className="text-zinc-600 shrink-0" />
          <AnimatePresence mode="wait">
            <motion.h1
              key={pathname}
              initial={{ opacity: 0, y: -3 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 3 }}
              transition={{ duration: 0.15 }}
              className="text-[15px] font-semibold text-white truncate tracking-tight"
            >
              {page.title}
            </motion.h1>
          </AnimatePresence>
        </div>

        {/* DFW market chip */}
        <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/[0.04] border border-white/[0.07] shrink-0">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" />
          <span className="text-[11px] font-medium text-zinc-500">DFW</span>
        </div>

        {/* User avatar */}
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-violet-600 flex items-center justify-center text-white text-xs font-bold ring-2 ring-white/[0.08] cursor-pointer hover:ring-white/20 transition-all shrink-0">
          E
        </div>
      </div>
    </header>
  )
}
