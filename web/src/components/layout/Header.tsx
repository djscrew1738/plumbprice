'use client'

import { usePathname } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import { Menu, Bell, HelpCircle, MessageSquare, FileText, Package, Layers, FileOutput, Settings } from 'lucide-react'

const pages: Record<string, { title: string; icon: typeof MessageSquare }> = {
  '/estimator': { title: 'Chat Estimator', icon: MessageSquare },
  '/estimates': { title: 'Estimates', icon: FileText },
  '/suppliers': { title: 'Suppliers', icon: Package },
  '/blueprints': { title: 'Blueprints', icon: Layers },
  '/proposals': { title: 'Proposals', icon: FileOutput },
  '/admin': { title: 'Admin', icon: Settings },
}

export function Header({ onMenuClick }: { onMenuClick: () => void }) {
  const pathname = usePathname()
  const page = pages[pathname] ?? { title: 'PlumbPrice AI', icon: MessageSquare }
  const PageIcon = page.icon

  return (
    <header className="bg-black/60 backdrop-blur-xl border-b border-white/5 sticky top-0 z-20"
      style={{ paddingTop: 'env(safe-area-inset-top)' }}>
      <div className="flex items-center h-14 px-4 gap-3">
        {/* Hamburger -- mobile only */}
        <button
          onClick={onMenuClick}
          className="lg:hidden p-2 -ml-2 rounded-lg text-zinc-400 hover:text-white hover:bg-white/10 transition-colors"
          aria-label="Open menu"
        >
          <Menu size={22} />
        </button>

        {/* Breadcrumb-style title */}
        <div className="flex-1 flex items-center gap-2 min-w-0">
          <PageIcon size={16} className="text-zinc-500 shrink-0" />
          <AnimatePresence mode="wait">
            <motion.h1
              key={pathname}
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 4 }}
              transition={{ duration: 0.15 }}
              className="text-[17px] font-semibold text-white truncate lg:text-lg tracking-tight"
            >
              {page.title}
            </motion.h1>
          </AnimatePresence>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-1">
          <button className="p-2 rounded-lg text-zinc-400 hover:text-white hover:bg-white/10 transition-colors">
            <HelpCircle size={20} />
          </button>
          <button className="p-2 rounded-lg text-zinc-400 hover:text-white hover:bg-white/10 transition-colors">
            <Bell size={20} />
          </button>
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-violet-500 flex items-center justify-center text-white text-sm font-bold ml-1 ring-2 ring-white/10 hover:ring-white/20 transition-all cursor-pointer">
            E
          </div>
        </div>
      </div>
    </header>
  )
}
