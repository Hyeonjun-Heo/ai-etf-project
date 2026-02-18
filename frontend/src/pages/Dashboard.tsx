import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import apiClient from '../api/client'
import MarketChart from '../components/charts/MarketChart'
import IndexTickerBar from '../components/common/IndexTickerBar'
import type { ChartPoint, EtfQuote, IndexQuote, IndexSparklines, Movers } from '../types/market'
import styles from './Dashboard.module.css'

export default function Dashboard() {
  const [indices, setIndices] = useState<IndexQuote[]>([])
  const [sparklines, setSparklines] = useState<IndexSparklines>({})
  const [etfs, setEtfs] = useState<EtfQuote[]>([])
  const [chart, setChart] = useState<ChartPoint[]>([])
  const [movers, setMovers] = useState<Movers>({ gainers: [], losers: [] })
  const [period, setPeriod] = useState('6mo')
  const [moverTab, setMoverTab] = useState<'gainers' | 'losers'>('gainers')
  const [loading, setLoading] = useState(true)
  const [chartLoading, setChartLoading] = useState(false)

  // Fetch all data on mount
  useEffect(() => {
    const load = async () => {
      setLoading(true)
      try {
        const [indicesRes, sparklinesRes, etfsRes, chartRes, moversRes] = await Promise.all([
          apiClient.get('/market/indices'),
          apiClient.get('/market/index-sparklines'),
          apiClient.get('/market/top-etfs'),
          apiClient.get(`/market/chart?symbol=SPY&period=${period}`),
          apiClient.get('/market/movers'),
        ])
        setIndices(indicesRes.data)
        setSparklines(sparklinesRes.data)
        setEtfs(etfsRes.data)
        setChart(chartRes.data)
        setMovers(moversRes.data)
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

  const formatChange = (change: number, pct: number) => {
    const sign = change >= 0 ? '+' : ''
    return `${sign}${change.toFixed(2)} (${sign}${pct.toFixed(2)}%)`
  }

  const activeMovers = moverTab === 'gainers' ? movers.gainers : movers.losers

  return (
    <div className={styles.page}>
      {/* ── Section 1: Market Overview (Ticker Bar) ── */}
      <IndexTickerBar indices={indices} sparklines={sparklines} isLoading={loading} />

      {/* ── Section 2: Chart + ETF Ranking (two columns) ── */}
      <div className={styles.columns}>
        <div>
          <MarketChart
            data={chart}
            activePeriod={period}
            onPeriodChange={handlePeriodChange}
            isLoading={loading || chartLoading}
          />
        </div>

        <div className={styles.tableCard}>
          <h2 className={styles.sectionTitle}>Top ETFs</h2>
          {loading ? (
            Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className={`${styles.skeleton} ${styles.skeletonRow}`} />
            ))
          ) : (
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Price</th>
                  <th>Change</th>
                </tr>
              </thead>
              <tbody>
                {etfs.map((etf) => (
                  <tr key={etf.symbol}>
                    <td><Link to={`/stock/${etf.symbol}`} className={styles.symbolBadge}>{etf.symbol}</Link></td>
                    <td>${etf.price.toFixed(2)}</td>
                    <td className={etf.changePct >= 0 ? styles.up : styles.down}>
                      {formatChange(etf.change, etf.changePct)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* ── Section 3: Market Movers ── */}
      <div className={styles.moversCard}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
          <h2 className={styles.sectionTitle} style={{ margin: 0 }}>Market Movers</h2>
          <div className={styles.tabs}>
            <button
              className={`${styles.tab} ${moverTab === 'gainers' ? styles.tabActive : ''}`}
              onClick={() => setMoverTab('gainers')}
            >
              Gainers
            </button>
            <button
              className={`${styles.tab} ${moverTab === 'losers' ? styles.tabActive : ''}`}
              onClick={() => setMoverTab('losers')}
            >
              Losers
            </button>
          </div>
        </div>

        {loading
          ? Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className={`${styles.skeleton} ${styles.skeletonRow}`} />
            ))
          : activeMovers.map((item) => (
              <div key={item.symbol} className={styles.moverRow}>
                <div>
                  <Link to={`/stock/${item.symbol}`} className={styles.moverSymbol}>{item.symbol}</Link>
                  <div className={styles.moverPrice}>${item.price.toFixed(2)}</div>
                </div>
                <span
                  className={`${styles.moverChange} ${
                    item.changePct >= 0 ? styles.moverUp : styles.moverDown
                  }`}
                >
                  {item.changePct >= 0 ? '+' : ''}{item.changePct.toFixed(2)}%
                </span>
              </div>
            ))}
      </div>
    </div>
  )
}
