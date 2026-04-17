'use client'

import { useState, useMemo, useId } from 'react'
import { cn } from '@/lib/utils'

export interface BarDatum {
  label: string
  value: number
}

export interface BarChartProps {
  data: BarDatum[]
  height?: number
  barColor?: string
  className?: string
  formatValue?: (v: number) => string
}

const PADDING_LEFT = 48
const PADDING_RIGHT = 12
const PADDING_TOP = 24
const PADDING_BOTTOM = 28
const GRID_LINES = 4

export function BarChart({
  data,
  height = 200,
  barColor = 'var(--accent)',
  className,
  formatValue = (v) => String(v),
}: BarChartProps) {
  const id = useId()
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null)

  const maxValue = useMemo(
    () => Math.max(...data.map((d) => d.value), 1),
    [data],
  )

  const chartW = 600
  const chartH = height
  const plotH = chartH - PADDING_TOP - PADDING_BOTTOM
  const plotW = chartW - PADDING_LEFT - PADDING_RIGHT

  const barCount = data.length || 1
  const gap = Math.min(12, plotW / barCount * 0.25)
  const barW = Math.max(8, (plotW - gap * (barCount + 1)) / barCount)

  const yTicks = useMemo(() => {
    const ticks: number[] = []
    for (let i = 0; i <= GRID_LINES; i++) {
      ticks.push(Math.round((maxValue / GRID_LINES) * i))
    }
    return ticks
  }, [maxValue])

  return (
    <div className={cn('w-full', className)}>
      <svg
        viewBox={`0 0 ${chartW} ${chartH}`}
        className="w-full"
        preserveAspectRatio="xMidYMid meet"
        role="img"
        aria-label="Bar chart"
      >
        {/* Grid lines + Y-axis labels */}
        {yTicks.map((tick) => {
          const y = PADDING_TOP + plotH - (tick / maxValue) * plotH
          return (
            <g key={`${id}-tick-${tick}`}>
              <line
                x1={PADDING_LEFT}
                x2={chartW - PADDING_RIGHT}
                y1={y}
                y2={y}
                stroke="var(--line)"
                strokeWidth={1}
                strokeDasharray="4 4"
              />
              <text
                x={PADDING_LEFT - 6}
                y={y + 4}
                textAnchor="end"
                fontSize={11}
                fill="var(--muted-ink)"
                fontFamily="inherit"
              >
                {formatValue(tick)}
              </text>
            </g>
          )
        })}

        {/* Bars */}
        {data.map((d, i) => {
          const barH = (d.value / maxValue) * plotH
          const x = PADDING_LEFT + gap + i * (barW + gap)
          const y = PADDING_TOP + plotH - barH

          return (
            <g
              key={`${id}-bar-${d.label}`}
              onMouseEnter={() => setHoveredIndex(i)}
              onMouseLeave={() => setHoveredIndex(null)}
              className="cursor-default"
            >
              {/* Bar */}
              <rect
                x={x}
                y={y}
                width={barW}
                height={barH}
                rx={4}
                fill={barColor}
                style={{
                  opacity: hoveredIndex === null || hoveredIndex === i ? 1 : 0.5,
                  transition: 'height 0.5s ease-out, y 0.5s ease-out, opacity 0.2s',
                }}
              />

              {/* Value label above bar */}
              <text
                x={x + barW / 2}
                y={y - 6}
                textAnchor="middle"
                fontSize={11}
                fontWeight={600}
                fill="var(--ink)"
                fontFamily="inherit"
                style={{
                  opacity: hoveredIndex === i ? 1 : 0.7,
                  transition: 'opacity 0.2s',
                }}
              >
                {formatValue(d.value)}
              </text>

              {/* X-axis label */}
              <text
                x={x + barW / 2}
                y={PADDING_TOP + plotH + 18}
                textAnchor="middle"
                fontSize={11}
                fill="var(--muted-ink)"
                fontFamily="inherit"
              >
                {d.label}
              </text>
            </g>
          )
        })}
      </svg>
    </div>
  )
}
