'use client'

import { usePathname } from 'next/navigation'
import Link from 'next/link'
import { motion } from 'framer-motion'
import { MessageSquare, FileText, Package, Settings, BriefcaseBusiness } from 'lucide-react'

const tabs = [
  { href: '/estimator', icon: MessageSquare,      label: 'Estimate' },
  { href: '/estimates', icon: FileText,           label: 'Saved' },
  { href: '/pipeline',  icon: BriefcaseBusiness,  label: 'Pipeline' },
  { href: '/suppliers', icon: Package,            label: 'Suppliers' },
  { href: '/admin',     icon: Settings,           label: 'Admin' },
]

export function MobileNav() {
  const pathname = usePathname()

  return (
    <nav
      className="fixed bottom-0 inset-x-0 bg-[#080808]/90 backdrop-blur-2xl border-t border-white/[0.06] z-40 lg:hidden"
      style={{ paddingBottom: 'max(env(safe-area-inset-bottom), 6px)' }}
    >
      <div className="flex">
        {tabs.map(({ href, icon: Icon, label }) => {
          const active = pathname === href || pathname.startsWith(href + '/') || (href === '/estimator' && pathname === '/')
          return (
            <Link
              key={href}
              href={href}
              className="relative flex-1 flex flex-col items-center justify-center pt-2 pb-1.5 gap-1 transition-colors duration-150 min-h-[52px]"
            >
              {active && (
                <motion.div
                  layoutId="mobileActiveTab"
                  className="absolute top-0 left-1/2 -translate-x-1/2 w-8 h-[2px] bg-blue-500 rounded-full"
                  transition={{ type: 'spring', stiffness: 500, damping: 35 }}
                />
              )}
              <div className={`flex items-center justify-center w-6 h-6 rounded-lg transition-all ${
                active ? 'text-blue-400' : 'text-zinc-600'
              }`}>
                <Icon size={21} strokeWidth={active ? 2.25 : 1.75} />
              </div>
              <span className={`text-[9px] font-semibold tracking-wide leading-none ${
                active ? 'text-blue-400' : 'text-zinc-600'
              }`}>
                {label}
              </span>
            </Link>
          )
        })}
      </div>
    </nav>
  )
}
