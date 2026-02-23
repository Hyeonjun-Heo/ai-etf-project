import { useEffect, useState } from 'react'
import apiClient from '../api/client'
import MarketChart from '../components/charts/MarketChart'
import IndexTickerBar from '../components/common/IndexTickerBar'
import RealTimeRanking from '../components/common/RealTimeRanking'
import type { ChartPoint, IndexQuote, IndexSparklines } from '../types/market'
import styles from './Dashboard.module.css'

export default function Dashboard() {
  const [indices, setIndices] = useState<IndexQuote[]>([])
  const [sparklines, setSparklines] = useState<IndexSparklines>({})
  const [chart, setChart] = useState<ChartPoint[]>([])
  const [period, setPeriod] = useState('6mo')
  const [loading, setLoading] = useState(true)
  const [chartLoading, setChartLoading] = useState(false)

  // Fetch all data on mount
  useEffect(() => {
    const load = async () => {
      setLoading(true)
      try {
        const [indicesRes, sparklinesRes, chartRes] = await Promise.all([
          apiClient.get('/market/indices'),
          apiClient.get('/market/index-sparklines'),
          apiClient.get(`/market/chart?symbol=SPY&period=${period}`),
        ])
        setIndices(indicesRes.data)
        setSparklines(sparklinesRes.data)
        setChart(chartRes.data)
      } catch {
        // silently fail — sections will show empty
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  // Fetch chart when period changes
  const handlePeriodChange = async (newPeriod: string) => {
    setPeriod(newPeriod)
    setChartLoading(true)
    try {
      const { data } = await apiClient.get(`/market/chart?symbol=SPY&period=${newPeriod}`)
      setChart(data)
    } catch {
      // keep old data
    } finally {
      setChartLoading(false)
    }
  }

  return (
    <div className={styles.page}>
      {/* ── Section 1: Market Overview (Ticker Bar) ── */}
      <IndexTickerBar indices={indices} sparklines={sparklines} isLoading={loading} />

      {/* ── Section 2: Chart (full width) ── */}
      <div className={styles.chartSection}>
        <MarketChart
          data={chart}
          activePeriod={period}
          onPeriodChange={handlePeriodChange}
          isLoading={loading || chartLoading}
        />
      </div>

      {/* ── Section 3: Real-Time Ranking ── */}
      <RealTimeRanking />
    </div>
  )
}
