'use client'

import { memo } from 'react'
import { motion, type Variants, type Transition } from 'framer-motion'
import { useReducedMotion } from '@/lib/useReducedMotion'

/* ═══════════════════════════════════════════════════════════════
   Reusable motion components for consistent animations across
   the app. All respect prefers-reduced-motion.
   ═══════════════════════════════════════════════════════════════ */

const defaultTransition: Transition = {
  duration: 0.2,
  ease: [0.16, 1, 0.3, 1], // --ease-out
}

const springTransition: Transition = {
  type: 'spring',
  damping: 28,
  stiffness: 320,
}

/* ── FadeIn ── */
interface FadeInProps {
  children: React.ReactNode
  delay?: number
  className?: string
  duration?: number
}

export const FadeIn = memo(function FadeIn({ children, delay = 0, className, duration = 0.2 }: FadeInProps) {
  const reduce = useReducedMotion()
  return (
    <motion.div
      className={className}
      initial={reduce ? { opacity: 0 } : { opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration, delay, ease: [0.16, 1, 0.3, 1] }}
    >
      {children}
    </motion.div>
  )
})

/* ── SlideUp ── */
interface SlideUpProps {
  children: React.ReactNode
  delay?: number
  className?: string
}

export const SlideUp = memo(function SlideUp({ children, delay = 0, className }: SlideUpProps) {
  const reduce = useReducedMotion()
  return (
    <motion.div
      className={className}
      initial={reduce ? { opacity: 0 } : { opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ ...springTransition, delay }}
    >
      {children}
    </motion.div>
  )
})

/* ── ScaleIn ── */
interface ScaleInProps {
  children: React.ReactNode
  className?: string
}

export const ScaleIn = memo(function ScaleIn({ children, className }: ScaleInProps) {
  const reduce = useReducedMotion()
  return (
    <motion.div
      className={className}
      initial={reduce ? { opacity: 0 } : { opacity: 0, scale: 0.96 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={defaultTransition}
    >
      {children}
    </motion.div>
  )
})

/* ── StaggerContainer ── */
const containerVariants: Variants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.06,
    },
  },
}

const itemVariants: Variants = {
  hidden: { opacity: 0, y: 8 },
  show: { opacity: 1, y: 0, transition: defaultTransition },
}

interface StaggerContainerProps {
  children: React.ReactNode
  className?: string
}

export const StaggerContainer = memo(function StaggerContainer({ children, className }: StaggerContainerProps) {
  const reduce = useReducedMotion()
  if (reduce) {
    return <div className={className}>{children}</div>
  }
  return (
    <motion.div
      className={className}
      variants={containerVariants}
      initial="hidden"
      animate="show"
    >
      {children}
    </motion.div>
  )
})

export const StaggerItem = memo(function StaggerItem({ children, className }: { children: React.ReactNode; className?: string }) {
  const reduce = useReducedMotion()
  if (reduce) {
    return <div className={className}>{children}</div>
  }
  return (
    <motion.div className={className} variants={itemVariants}>
      {children}
    </motion.div>
  )
})

/* ── SlideInRight / SlideInLeft (for drawers/sheets) ── */
interface SlideInProps {
  children: React.ReactNode
  direction?: 'left' | 'right' | 'bottom'
  className?: string
}

export const SlideIn = memo(function SlideIn({ children, direction = 'right', className }: SlideInProps) {
  const reduce = useReducedMotion()
  const x = direction === 'left' ? '-100%' : direction === 'right' ? '100%' : 0
  const y = direction === 'bottom' ? '100%' : 0

  return (
    <motion.div
      className={className}
      initial={reduce ? { opacity: 0 } : { x, y }}
      animate={{ x: 0, y: 0 }}
      exit={reduce ? { opacity: 0 } : { x, y }}
      transition={springTransition}
    >
      {children}
    </motion.div>
  )
})

/* ── Pulse (subtle attention) ── */
export const Pulse = memo(function Pulse({ children, className }: { children: React.ReactNode; className?: string }) {
  const reduce = useReducedMotion()
  return (
    <motion.div
      className={className}
      animate={reduce ? {} : { scale: [1, 1.02, 1] }}
      transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
    >
      {children}
    </motion.div>
  )
})
