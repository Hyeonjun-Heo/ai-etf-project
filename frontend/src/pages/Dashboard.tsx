import { useEffect, useState } from 'react'
import apiClient from '../api/client'
import IndexTickerBar from '../components/common/IndexTickerBar'
import RealTimeRanking from '../components/common/RealTimeRanking'
import type { IndexQuote, IndexSparklines } from '../types/market'
import styles from './Dashboard.module.css'

export default function Dashboard() {
  const [indices, setIndices] = useState<IndexQuote[]>([])
  const [sparklines, setSparklines] = useState<IndexSparklines>({})
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      try {
        const [indicesRes, sparklinesRes] = await Promise.all([
          apiClient.get('/market/indices'),
          apiClient.get('/market/index-sparklines'),
        ])
        setIndices(indicesRes.data)
        setSparklines(sparklinesRes.data)
      } catch {
        // silently fail — sections will show empty
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  return (
    <div className={styles.page}>
      {/* ── Section 1: Market Overview (Ticker Bar) ── */}
      <IndexTickerBar indices={indices} sparklines={sparklines} isLoading={loading} />

      {/* ── Section 2: Real-Time Ranking ── */}
      <RealTimeRanking />
    </div>
  )
}
