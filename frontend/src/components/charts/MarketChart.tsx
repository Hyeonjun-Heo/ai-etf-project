import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { ChartPoint } from '../../types/market'
import styles from './MarketChart.module.css'

const DEFAULT_PERIODS = ['1mo', '3mo', '6mo', '1y'] as const

interface Props {
  data: ChartPoint[]
  onPeriodChange: (period: string) => void
  activePeriod: string
  isLoading?: boolean
  title?: string
  periods?: readonly string[]
}

export default function MarketChart({
  data,
  onPeriodChange,
  activePeriod,
  isLoading,
  title = 'S&P 500',
  periods = DEFAULT_PERIODS,
}: Props) {
  return (
    <div className={styles.wrapper}>
      <div className={styles.header}>
        <h2 className={styles.title}>{title}</h2>
        <div className={styles.periods}>
          {periods.map((p) => (
            <button
              key={p}
              className={`${styles.periodBtn} ${activePeriod === p ? styles.active : ''}`}
              onClick={() => onPeriodChange(p)}
            >
              {p.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      <div className={styles.chartArea}>
        {isLoading ? (
          <div className={styles.skeleton} />
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={data}>
              <defs>
                <linearGradient id="colorClose" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#2563eb" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#2563eb" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="#1f2937" strokeDasharray="3 3" />
              <XAxis
                dataKey="date"
                tick={{ fill: '#6b7280', fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v: string) => v.slice(5)}
              />
              <YAxis
                tick={{ fill: '#6b7280', fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                domain={['auto', 'auto']}
                width={60}
              />
              <Tooltip
                contentStyle={{
                  background: '#1f2937',
                  border: '1px solid #374151',
                  borderRadius: 8,
                  color: '#e5e7eb',
                  fontSize: 13,
                }}
              />
              <Area
                type="monotone"
                dataKey="close"
                stroke="#2563eb"
                strokeWidth={2}
                fill="url(#colorClose)"
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  )
}
