'use client'

import { memo } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { motion } from 'framer-motion'
import { MOBILE_TABS, matchesPathname } from './nav'
import { useReducedMotion } from '@/lib/useReducedMotion'

export const MobileNav = memo(function MobileNav({ onOpenMore }: { onOpenMore: () => void }) {
  const pathname = usePathname()
  const reduce = useReducedMotion()

  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-40 border-t border-[color:var(--line)] bg-[color:var(--panel)]/95 backdrop-blur-xl lg:hidden"
      aria-label="Bottom navigation"
    >
      <div className="grid grid-cols-4 px-2 pb-[max(env(safe-area-inset-bottom),10px)] pt-2">
        {MOBILE_TABS.map(({ href, icon: Icon, label }) => {
          if (href === '#more') {
            return (
              <button
                key={label}
                type="button"
                onClick={onOpenMore}
                className="relative flex min-h-[58px] flex-col items-center justify-center gap-1 rounded-[1.25rem] text-[11px] font-semibold text-[color:var(--muted-ink)] transition-colors hover:bg-[color:var(--panel-strong)]"
                aria-label={label}
              >
                <Icon size={20} />
                <span>{label}</span>
              </button>
            )
          }

          const active = matchesPathname(pathname, href)

          return (
            <Link
              key={href}
              href={href}
              className="relative flex min-h-[58px] flex-col items-center justify-center gap-1 rounded-[1.25rem] text-[11px] font-semibold"
              aria-current={active ? 'page' : undefined}
            >
              {active && (
                <motion.span
                  layoutId={reduce ? undefined : 'mobile-tab-indicator'}
                  className="absolute inset-x-3 top-0 h-[3px] rounded-full bg-[color:var(--accent)]"
                  transition={reduce ? { duration: 0 } : { duration: 0.2, ease: 'easeOut' }}
                />
              )}
              <Icon
                size={20}
                className={active ? 'text-[color:var(--accent-strong)]' : 'text-[color:var(--muted-ink)]'}
                aria-hidden="true"
              />
              <span className={active ? 'text-[color:var(--ink)]' : 'text-[color:var(--muted-ink)]'}>
                {label}
              </span>
            </Link>
          )
        })}
      </div>
    </nav>
  )
})
