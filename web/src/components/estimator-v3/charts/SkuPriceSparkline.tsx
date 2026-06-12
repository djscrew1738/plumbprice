'use client'

import { LineChart, Line, ResponsiveContainer } from 'recharts'
import { cn } from '@/lib/utils'

interface SkuPriceSparklineProps {
  data?: Array<{ date: string; price: number }>
  className?: string
}

const MOCK_DATA = [
  { date: '2026-03-01', price: 145 },
  { date: '2026-03-15', price: 148 },
  { date: '2026-04-01', price: 142 },
  { date: '2026-04-15', price: 150 },
  { date: '2026-05-01', price: 155 },
  { date: '2026-05-15', price: 152 },
  { date: '2026-06-01', price: 158 },
]

export function SkuPriceSparkline({ data, className }: SkuPriceSparklineProps) {
  const chartData = data && data.length > 0 ? data : MOCK_DATA
  const trend = chartData[chartData.length - 1].price >= chartData[0].price

  return (
    <div className={cn('w-16 h-6', className)}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData}>
          <Line
            type="monotone"
            dataKey="price"
            stroke={trend ? '#10b981' : '#ef4444'}
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
