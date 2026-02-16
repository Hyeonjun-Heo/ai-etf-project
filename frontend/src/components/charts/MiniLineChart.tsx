import { Line, LineChart, ResponsiveContainer } from 'recharts'

interface Props {
  data: { date: string; close: number }[]
  color?: string
  height?: number
}

export default function MiniLineChart({ data, color = '#2563eb', height = 40 }: Props) {
  if (data.length === 0) return null

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data}>
        <Line
          type="monotone"
          dataKey="close"
          stroke={color}
          strokeWidth={1.5}
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
