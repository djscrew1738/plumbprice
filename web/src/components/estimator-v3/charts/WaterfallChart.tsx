'use client'

import { useMemo, useState } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import { cn } from '@/lib/utils'

interface WaterfallData {
  name: string
  value: number
  color: string
}

interface WaterfallChartProps {
  data: WaterfallData[]
  total: number
  className?: string
}

export function WaterfallChart({ data, total, className }: WaterfallChartProps) {
  const [hovered, setHovered] = useState<string | null>(null)

  const chartData = useMemo(() => {
    let running = 0
    return data.map(item => {
      const start = running
      running += item.value
      return {
        name: item.name,
        start,
        value: item.value,
        end: running,
        color: item.color,
        pct: (item.value / total) * 100,
      }
    })
  }, [data, total])

  return (
    <div className={cn('w-full', className)}>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={chartData} margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
          <XAxis
            dataKey="name"
            tick={{ fontSize: 10, fill: 'var(--muted-ink)' }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis hide />
          <Tooltip
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null
              const p = payload[0].payload
              return (
                <div className="rounded-lg border border-[color:var(--line)] bg-[color:var(--panel)] px-3 py-2 text-xs shadow-lg">
                  <p className="font-semibold text-[color:var(--ink)]">{p.name}</p>
                  <p className="text-[color:var(--muted-ink)]">${p.value.toLocaleString('en-US', { minimumFractionDigits: 2 })}</p>
                  <p className="text-[10px] text-[color:var(--muted-ink)]">{p.pct.toFixed(1)}% of total</p>
                </div>
              )
            }}
          />
          {/* Invisible base bar */}
          <Bar dataKey="start" stackId="a" fill="transparent" isAnimationActive={false} />
          {/* Visible value bar */}
          <Bar
            dataKey="value"
            stackId="a"
            radius={[4, 4, 0, 0]}
            isAnimationActive={false}
          >
            {chartData.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={entry.color}
                opacity={hovered === entry.name ? 1 : 0.85}
                onMouseEnter={() => setHovered(entry.name)}
                onMouseLeave={() => setHovered(null)}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
