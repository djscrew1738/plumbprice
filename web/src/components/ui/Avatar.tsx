'use client'

import { useState, memo } from 'react'
import Image from 'next/image'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

/* ── Size variants ───────────────────────────────── */

const avatarVariants = cva(
  'relative inline-flex items-center justify-center rounded-full ring-2 ring-[color:var(--panel)] shrink-0 overflow-hidden',
  {
    variants: {
      size: {
        sm: 'h-7 w-7 text-[10px]',
        md: 'h-9 w-9 text-xs',
        lg: 'h-11 w-11 text-sm',
        xl: 'h-14 w-14 text-base',
      },
    },
    defaultVariants: { size: 'md' },
  },
)

/* ── Status dot sizing ───────────────────────────── */

const dotSize: Record<string, string> = {
  sm: 'h-2 w-2',
  md: 'h-2.5 w-2.5',
  lg: 'h-3 w-3',
  xl: 'h-3.5 w-3.5',
}

const statusColor: Record<string, string> = {
  online: 'bg-emerald-500',
  offline: 'bg-zinc-400',
  busy: 'bg-red-500',
  away: 'bg-amber-500',
}

/* ── Types ───────────────────────────────────────── */

export interface AvatarProps extends VariantProps<typeof avatarVariants> {
  src?: string
  alt?: string
  fallback?: string
  status?: 'online' | 'offline' | 'busy' | 'away'
  className?: string
}

/* ── Pixel sizes for next/image ───────────────────── */

const pixelSize: Record<string, number> = {
  sm: 28,
  md: 36,
  lg: 44,
  xl: 56,
}

/* ── Avatar ──────────────────────────────────────── */

export const Avatar = memo(function Avatar({
  src,
  alt = '',
  fallback,
  size,
  status,
  className,
}: AvatarProps) {
  const [imgError, setImgError] = useState(false)
  const showImage = src && !imgError

  const sizeKey = size ?? 'md'
  const px = pixelSize[sizeKey]

  return (
    <span className={cn(avatarVariants({ size }), className)}>
      {showImage ? (
        <Image
          src={src}
          alt={alt}
          width={px}
          height={px}
          className="h-full w-full object-cover rounded-full"
          onError={() => setImgError(true)}
          unoptimized
        />
      ) : (
        <span
          className="flex h-full w-full items-center justify-center rounded-full bg-[color:var(--accent-soft)] text-[color:var(--accent-strong)] font-semibold select-none"
          aria-hidden={!!alt ? undefined : 'true'}
        >
          {fallback ?? alt?.charAt(0)?.toUpperCase() ?? '?'}
        </span>
      )}

      {status && (
        <span
          className={cn(
            'absolute bottom-0 right-0 rounded-full ring-2 ring-[color:var(--panel)]',
            dotSize[sizeKey],
            statusColor[status],
          )}
          role="status"
          aria-label={status}
        />
      )}
    </span>
  )
})
