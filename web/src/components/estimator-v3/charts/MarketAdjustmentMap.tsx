'use client'

import { useState } from 'react'
import { cn } from '@/lib/utils'

// Simplified DFW county polygons (normalized 0-100 coordinate space)
const COUNTIES = [
  { name: 'Dallas', path: 'M45,35 L55,35 L58,45 L55,55 L45,58 L40,48 Z', factor: 1.08 },
  { name: 'Tarrant', path: 'M25,30 L40,30 L42,45 L38,55 L28,52 L22,42 Z', factor: 1.05 },
  { name: 'Collin', path: 'M45,15 L62,18 L65,30 L58,38 L48,35 L42,25 Z', factor: 1.03 },
  { name: 'Denton', path: 'M28,12 L45,15 L48,28 L42,35 L30,32 L25,22 Z', factor: 1.02 },
  { name: 'Rockwall', path: 'M58,28 L68,28 L70,38 L65,42 L58,38 Z', factor: 1.01 },
  { name: 'Kaufman', path: 'M60,45 L72,48 L75,58 L68,65 L58,58 Z', factor: 1.0 },
  { name: 'Ellis', path: 'M38,58 L52,58 L55,72 L48,78 L35,72 Z', factor: 1.01 },
  { name: 'Johnson', path: 'M18,55 L32,55 L35,70 L28,75 L15,68 Z', factor: 1.0 },
]

function intensityColor(factor: number): string {
  if (factor >= 1.10) return '#dc2626' // red-600
  if (factor >= 1.07) return '#ea580c' // orange-600
  if (factor >= 1.04) return '#ca8a04' // yellow-600
  if (factor >= 1.01) return '#16a34a' // green-600
  return '#71717a' // zinc-500
}

interface MarketAdjustmentMapProps {
  adjustments?: Array<{ name: string; factor: number }>
  className?: string
}

export function MarketAdjustmentMap({ adjustments, className }: MarketAdjustmentMapProps) {
  const [hovered, setHovered] = useState<string | null>(null)

  const factorMap = new Map(adjustments?.map(a => [a.name, a.factor]) || [])

  return (
    <div className={cn('w-full', className)}>
      <svg viewBox="0 0 100 90" className="w-full h-auto">
        {COUNTIES.map(county => {
          const factor = factorMap.get(county.name) || county.factor
          const color = intensityColor(factor)
          const isHovered = hovered === county.name
          return (
            <g key={county.name}>
              <path
                d={county.path}
                fill={color}
                stroke="var(--line)"
                strokeWidth={0.8}
                opacity={isHovered ? 1 : 0.75}
                className="transition-opacity cursor-pointer"
                onMouseEnter={() => setHovered(county.name)}
                onMouseLeave={() => setHovered(null)}
              />
              <text
                x={county.path.match(/M(\d+)/)?.[1] || 0}
                y={county.path.match(/,(\d+)/)?.[1] || 0}
                fontSize="3"
                fill="white"
                opacity={0.9}
                pointerEvents="none"
                transform="translate(4, 8)"
              >
                {county.name}
              </text>
            </g>
          )
        })}
      </svg>
      {hovered && (
        <div className="mt-2 rounded-lg border border-[color:var(--line)] bg-[color:var(--panel-strong)] px-3 py-2 text-xs">
          <span className="font-semibold text-[color:var(--ink)]">{hovered}</span>
          <span className="ml-2 text-[color:var(--muted-ink)]">
            Adjustment: ×{(factorMap.get(hovered) || 1.0).toFixed(3)}
          </span>
        </div>
      )}
    </div>
  )
}
