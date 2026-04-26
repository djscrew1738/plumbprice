import { FOOTER_LINE, BUILT_BY_LINE } from '@/lib/branding'

interface BrandFooterProps {
  /** Show the "Built by Cory Nichols" credit line below the product line. */
  withCredit?: boolean
  /** Extra text to prepend to the product line (e.g., estimate id). */
  prefix?: string
  className?: string
}

/**
 * Small, subtle product + owner credit footer. Intentionally low-contrast
 * (text-zinc-600/zinc-700) so it never competes with primary content.
 */
export function BrandFooter({ withCredit = true, prefix, className = '' }: BrandFooterProps) {
  return (
    <div className={`text-center text-[11px] leading-relaxed text-zinc-600 dark:text-zinc-700 print:text-zinc-500 ${className}`}>
      <p>{prefix ? `${prefix} · ${FOOTER_LINE}` : FOOTER_LINE}</p>
      {withCredit && <p className="mt-1 text-zinc-700 dark:text-zinc-800">{BUILT_BY_LINE}</p>}
    </div>
  )
}
