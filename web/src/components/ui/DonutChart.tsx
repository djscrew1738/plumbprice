'use client'

import { useState, useMemo, useId, memo } from 'react'
import { cn, formatCurrency } from '@/lib/utils'

export interface DonutSegment {
  label: string
  value: number
  color: string
}

export interface DonutChartProps {
  data: DonutSegment[]
  size?: number
  thickness?: number
  className?: string
  showLegend?: boolean
}

export const DonutChart = memo(function DonutChart({
  data,
  size = 200,
  thickness = 30,
  className,
  showLegend = true,
}: DonutChartProps) {
  const id = useId()
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null)

  const total = useMemo(
    () => data.reduce((sum, d) => sum + d.value, 0),
    [data],
  )

  const radius = (size - thickness) / 2
  const circumference = 2 * Math.PI * radius
  const center = size / 2

  const segments = useMemo(() => {
    let accumulated = 0
    return data.map((d) => {
      const pct = total > 0 ? d.value / total : 0
      const dashArray = pct * circumference
      const dashOffset = -accumulated * circumference
      accumulated += pct
      return { ...d, pct, dashArray, dashOffset }
    })
  }, [data, total, circumference])

  return (
    <div className={cn('flex flex-col items-center gap-4', className)}>
      {/* SVG donut */}
      <div className="relative" style={{ width: size, height: size }}>
        <svg
          width={size}
          height={size}
          viewBox={`0 0 ${size} ${size}`}
          className="block"
          role="img"
          aria-label="Cost breakdown donut chart"
        >
          {/* Background ring */}
          <circle
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            stroke="var(--line)"
            strokeWidth={thickness}
          />

          {/* Segments – rendered on top */}
          {segments.map((seg, i) => (
            <circle
              key={`${id}-seg-${seg.label}`}
              cx={center}
              cy={center}
              r={radius}
              fill="none"
              stroke={seg.color}
              strokeWidth={thickness}
              strokeDasharray={`${seg.dashArray} ${circumference - seg.dashArray}`}
              strokeDashoffset={seg.dashOffset}
              strokeLinecap="butt"
              className="origin-center -rotate-90 transition-all duration-700 ease-out"
              style={{
                opacity: hoveredIndex === null || hoveredIndex === i ? 1 : 0.4,
                transform: `rotate(-90deg)${hoveredIndex === i ? ' scale(1.04)' : ''}`,
                transformOrigin: `${center}px ${center}px`,
                transition: 'stroke-dashoffset 0.7s ease-out, opacity 0.2s, transform 0.2s',
              }}
              onMouseEnter={() => setHoveredIndex(i)}
              onMouseLeave={() => setHoveredIndex(null)}
            />
          ))}
        </svg>

        {/* Center label */}
        <div
          className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none"
        >
          {hoveredIndex !== null ? (
            <>
              <span className="text-[10px] font-medium text-[color:var(--muted-ink)]">
                {segments[hoveredIndex].label}
              </span>
              <span className="text-sm font-bold text-[color:var(--ink)] tabular-nums">
                {Math.round(segments[hoveredIndex].pct * 100)}%
              </span>
            </>
          ) : (
            <>
              <span className="text-[10px] font-medium text-[color:var(--muted-ink)]">Total</span>
              <span className="text-sm font-bold text-[color:var(--ink)] tabular-nums">
                {formatCurrency(total)}
              </span>
            </>
          )}
        </div>
      </div>

      {/* Legend */}
      {showLegend && (
        <ul className="flex flex-wrap justify-center gap-x-4 gap-y-1.5 text-xs">
          {segments.map((seg, i) => (
            <li
              key={`${id}-legend-${seg.label}`}
              className="flex items-center gap-1.5 cursor-default"
              onMouseEnter={() => setHoveredIndex(i)}
              onMouseLeave={() => setHoveredIndex(null)}
            >
              <span
                className="inline-block size-2.5 rounded-full shrink-0"
                style={{ backgroundColor: seg.color }}
              />
              <span className="text-[color:var(--muted-ink)]">{seg.label}</span>
              <span className="font-semibold text-[color:var(--ink)] tabular-nums">
                {formatCurrency(seg.value)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
})
