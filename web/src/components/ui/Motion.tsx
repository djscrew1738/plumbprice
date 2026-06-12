'use client'

import { memo, useEffect, useRef, useState, type ElementType } from 'react'
import { motion, type Variants, type Transition, AnimatePresence } from 'framer-motion'
import { useReducedMotion } from '@/lib/useReducedMotion'

/* ═══════════════════════════════════════════════════════════════
   Shared animation constants and reusable motion components.
   All primitives respect prefers-reduced-motion.
   ═══════════════════════════════════════════════════════════════ */

export const MOTION = {
  duration: { fast: 0.15, normal: 0.2, slow: 0.35 },
  ease: [0.16, 1, 0.3, 1] as const,
  spring: { type: 'spring' as const, damping: 28, stiffness: 320 },
  gentleSpring: { type: 'spring' as const, damping: 24, stiffness: 220 },
  stagger: 0.04,
}

const defaultTransition: Transition = {
  duration: MOTION.duration.normal,
  ease: [...MOTION.ease],
}

const springTransition: Transition = { ...MOTION.spring }

/* ── FadeIn ── */
interface FadeInProps {
  children: React.ReactNode
  delay?: number
  className?: string
  duration?: number
}

export const FadeIn = memo(function FadeIn({ children, delay = 0, className, duration = MOTION.duration.normal }: FadeInProps) {
  const reduce = useReducedMotion()
  return (
    <motion.div
      className={className}
      initial={reduce ? { opacity: 0.8 } : { opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration, delay, ease: [...MOTION.ease] }}
    >
      {children}
    </motion.div>
  )
})

/* ── BlurFade ── */
interface BlurFadeProps {
  children: React.ReactNode
  delay?: number
  className?: string
  duration?: number
}

export const BlurFade = memo(function BlurFade({ children, delay = 0, className, duration = MOTION.duration.slow }: BlurFadeProps) {
  const reduce = useReducedMotion()
  return (
    <motion.div
      className={className}
      initial={reduce ? { opacity: 0.8 } : { opacity: 0, y: 8, filter: 'blur(4px)' }}
      animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
      transition={{ duration, delay, ease: [...MOTION.ease] }}
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
  duration?: number
}

export const SlideUp = memo(function SlideUp({ children, delay = 0, className, duration }: SlideUpProps) {
  const reduce = useReducedMotion()
  return (
    <motion.div
      className={className}
      initial={reduce ? { opacity: 0.8 } : { opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={duration ? { duration, delay, ease: [...MOTION.ease] } : { ...springTransition, delay }}
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
      initial={reduce ? { opacity: 0.8 } : { opacity: 0, scale: 0.96 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={defaultTransition}
    >
      {children}
    </motion.div>
  )
})

/* ── Reveal (scroll-triggered) ── */
interface RevealProps {
  children: React.ReactNode
  className?: string
  delay?: number
  direction?: 'up' | 'down' | 'left' | 'right'
  distance?: number
}

export const Reveal = memo(function Reveal({
  children,
  className,
  delay = 0,
  direction = 'up',
  distance = 12,
}: RevealProps) {
  const reduce = useReducedMotion()
  const offsets = {
    up: { y: distance },
    down: { y: -distance },
    left: { x: distance },
    right: { x: -distance },
  }

  return (
    <motion.div
      className={className}
      initial={reduce ? { opacity: 0.8 } : { opacity: 0, ...offsets[direction] }}
      whileInView={{ opacity: 1, x: 0, y: 0 }}
      viewport={{ once: true, amount: 0.2 }}
      transition={{ duration: MOTION.duration.slow, delay, ease: [...MOTION.ease] }}
    >
      {children}
    </motion.div>
  )
})

/* ── Pressable ── */
interface PressableProps {
  children: React.ReactNode
  className?: string
  hoverScale?: number
  tapScale?: number
  lift?: boolean
}

export const Pressable = memo(function Pressable({
  children,
  className,
  hoverScale = 1.01,
  tapScale = 0.98,
  lift = false,
}: PressableProps) {
  const reduce = useReducedMotion()
  return (
    <motion.div
      className={className}
      whileHover={reduce ? undefined : { scale: hoverScale, y: lift ? -2 : 0 }}
      whileTap={reduce ? undefined : { scale: tapScale }}
      transition={springTransition}
    >
      {children}
    </motion.div>
  )
})

/* ── CountUp ── */
interface CountUpProps {
  value: number
  className?: string
  duration?: number
  formatter?: (n: number) => string
  /** @deprecated Use `value` */
  to?: number
}

export const CountUp = memo(function CountUp({
  value: valueProp,
  to,
  className,
  duration = MOTION.duration.slow,
  formatter = (n) => n.toLocaleString(),
}: CountUpProps) {
  const reduce = useReducedMotion()
  const value = to ?? valueProp
  const [display, setDisplay] = useState(value)
  const startRef = useRef<number | null>(null)
  const fromRef = useRef(value)
  const displayRef = useRef(display)

  useEffect(() => {
    displayRef.current = display
  }, [display])

  useEffect(() => {
    if (reduce) {
      setDisplay(value)
      return
    }
    fromRef.current = displayRef.current
    startRef.current = null
    let raf: number

    const step = (ts: number) => {
      if (startRef.current === null) startRef.current = ts
      const progress = Math.min((ts - startRef.current) / (duration * 1000), 1)
      const eased = 1 - Math.pow(1 - progress, 3) // ease-out-cubic
      const next = fromRef.current + (value - fromRef.current) * eased
      setDisplay(next)
      if (progress < 1) raf = requestAnimationFrame(step)
    }

    raf = requestAnimationFrame(step)
    return () => cancelAnimationFrame(raf)
  }, [value, duration, reduce])

  return <span className={className}>{formatter(display)}</span>
})

/* ── StaggerContainer / StaggerItem ── */
const itemVariants: Variants = {
  hidden: { opacity: 0, y: 8 },
  show: { opacity: 1, y: 0, transition: defaultTransition },
}

interface StaggerContainerProps extends React.HTMLAttributes<HTMLElement> {
  children: React.ReactNode
  className?: string
  as?: ElementType
  stagger?: number
  initialDelay?: number
}

export const StaggerContainer = memo(function StaggerContainer({
  children,
  className,
  as: Comp = 'div',
  stagger = MOTION.stagger,
  initialDelay = 0,
}: StaggerContainerProps) {
  const reduce = useReducedMotion()
  const variants: Variants = {
    hidden: { opacity: 1 },
    show: {
      opacity: 1,
      transition: { staggerChildren: stagger, delayChildren: initialDelay },
    },
  }
  if (reduce) {
    return <Comp className={className}>{children}</Comp>
  }
  return (
    <motion.div
      className={className}
      variants={variants}
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

/* ── SlideInRight / SlideInLeft / SlideInBottom (for drawers/sheets) ── */
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
      initial={reduce ? { opacity: 0.8 } : { x, y }}
      animate={{ x: 0, y: 0 }}
      exit={reduce ? { opacity: 0 } : { x, y }}
      transition={springTransition}
    >
      {children}
    </motion.div>
  )
})

/* ── SmoothPresence ── */
interface SmoothPresenceProps {
  children: React.ReactNode
  mode?: 'sync' | 'wait' | 'popLayout'
  initial?: boolean
}

export const SmoothPresence = memo(function SmoothPresence({
  children,
  mode = 'wait',
  initial = false,
}: SmoothPresenceProps) {
  return (
    <AnimatePresence mode={mode} initial={initial}>
      {children}
    </AnimatePresence>
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

/* ── HeightAuto (accordion-style height animation) ── */
interface HeightAutoProps {
  children: React.ReactNode
  className?: string
  /** If omitted, animates from 0 to auto whenever children mount. */
  open?: boolean
}

export const HeightAuto = memo(function HeightAuto({ children, className, open }: HeightAutoProps) {
  const reduce = useReducedMotion()
  return (
    <motion.div
      className={className}
      initial={open === undefined ? { height: 0, opacity: 0 } : false}
      animate={{
        height: open === false ? 0 : 'auto',
        opacity: open === false ? 0 : 1,
      }}
      exit={{ height: 0, opacity: 0 }}
      transition={reduce ? { duration: 0 } : defaultTransition}
      style={{ overflow: 'hidden' }}
    >
      {children}
    </motion.div>
  )
})

/* ── Shimmer (skeleton shine wrapper) ── */
interface ShimmerProps {
  children: React.ReactNode
  className?: string
}

export const Shimmer = memo(function Shimmer({ children, className }: ShimmerProps) {
  return (
    <div className={cn('relative overflow-hidden', className)}>
      <div className="pointer-events-none absolute inset-0 -translate-x-full animate-[shimmer_1.5s_infinite] bg-gradient-to-r from-transparent via-white/10 to-transparent" />
      {children}
    </div>
  )
})

/* Utility cn needed by Shimmer */
function cn(...inputs: (string | false | null | undefined)[]): string {
  return inputs.filter(Boolean).join(' ')
}
