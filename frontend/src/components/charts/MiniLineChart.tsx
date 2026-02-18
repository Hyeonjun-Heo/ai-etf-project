import { useMemo } from 'react'
import { Line, LineChart, ReferenceLine, ResponsiveContainer, YAxis } from 'recharts'

interface Props {
  data: { date: string; close: number }[]
  color?: string
  height?: number
  previousClose?: number | null
}

export default function MiniLineChart({ data, color = '#2563eb', height = 40, previousClose }: Props) {
  if (data.length === 0) return null

  const domain = useMemo(() => {
    const closes = data.map((d) => d.close)
    let min = Math.min(...closes)
    let max = Math.max(...closes)
    if (previousClose != null) {
      min = Math.min(min, previousClose)
      max = Math.max(max, previousClose)
    }
    const padding = (max - min) * 0.1 || 1
    return [min - padding, max + padding] as [number, number]
  }, [data, previousClose])

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data}>
        <YAxis domain={domain} hide />
        {previousClose != null && (
          <ReferenceLine
            y={previousClose}
            stroke="#6b7280"
            strokeDasharray="3 3"
            strokeWidth={1}
          />
        )}
        <Line
          type="monotone"
          dataKey="close"
          stroke={color}
          strokeWidth={1.5}
          dot={false}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
