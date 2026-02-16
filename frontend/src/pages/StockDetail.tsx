import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import apiClient from '../api/client'
import MarketChart from '../components/charts/MarketChart'
import type { ChartPoint, StockDetail as StockDetailType } from '../types/market'
import styles from './StockDetail.module.css'

const PERIODS = ['1d', '1w', '1mo', '3mo', '6mo', '1y'] as const

export default function StockDetail() {
  const { symbol } = useParams<{ symbol: string }>()
  const [stock, setStock] = useState<StockDetailType | null>(null)
  const [chart, setChart] = useState<ChartPoint[]>([])
  const [period, setPeriod] = useState('6mo')
  const [loading, setLoading] = useState(true)
  const [chartLoading, setChartLoading] = useState(false)
  const [error, setError] = useState(false)

  useEffect(() => {
    if (!symbol) return
    const upperSymbol = symbol.toUpperCase()

    const load = async () => {
      setLoading(true)
      setError(false)
      try {
        const [detailRes, chartRes] = await Promise.all([
          apiClient.get(`/market/stock/${upperSymbol}`),
          apiClient.get(`/market/chart?symbol=${upperSymbol}&period=${period}`),
        ])
        setStock(detailRes.data)
        setChart(chartRes.data)
      } catch {
        setError(true)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [symbol])

  const handlePeriodChange = async (newPeriod: string) => {
    if (!symbol) return
    setPeriod(newPeriod)
    setChartLoading(true)
    try {
      const { data } = await apiClient.get(
        `/market/chart?symbol=${symbol.toUpperCase()}&period=${newPeriod}`,
      )
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

  const formatNumber = (value: number | null | undefined) => {
    if (value == null) return 'N/A'
    return value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  }

  const formatMarketCap = (value: number | null | undefined) => {
    if (value == null) return 'N/A'
    if (value >= 1e12) return `$${(value / 1e12).toFixed(2)}T`
    if (value >= 1e9) return `$${(value / 1e9).toFixed(2)}B`
    if (value >= 1e6) return `$${(value / 1e6).toFixed(2)}M`
    return `$${value.toLocaleString()}`
  }

  const formatVolume = (value: number | null | undefined) => {
    if (value == null) return 'N/A'
    if (value >= 1e6) return `${(value / 1e6).toFixed(2)}M`
    if (value >= 1e3) return `${(value / 1e3).toFixed(1)}K`
    return value.toLocaleString()
  }

  const formatPercent = (value: number | null | undefined) => {
    if (value == null) return 'N/A'
    return `${(value * 100).toFixed(2)}%`
  }

  if (error) {
    return (
      <div className={styles.page}>
        <div className={styles.errorCard}>
          <div className={styles.errorTitle}>종목을 찾을 수 없습니다</div>
          <div className={styles.errorMessage}>
            "{symbol}" 심볼에 해당하는 종목 정보를 불러올 수 없습니다.
          </div>
          <Link to="/" className={styles.backLink}>
            대시보드로 돌아가기
          </Link>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className={styles.page}>
        <div className={`${styles.skeleton} ${styles.skeletonHeader}`} />
        <div className={`${styles.skeleton} ${styles.skeletonChart}`} />
        <div className={styles.statsGrid}>
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className={`${styles.skeleton} ${styles.skeletonStat}`} />
          ))}
        </div>
      </div>
    )
  }

  if (!stock) return null

  const stats = [
    { label: 'Market Cap', value: formatMarketCap(stock.marketCap) },
    { label: 'P/E Ratio', value: stock.peRatio != null ? stock.peRatio.toFixed(2) : 'N/A' },
    { label: 'Dividend Yield', value: formatPercent(stock.dividendYield) },
    {
      label: '52W Range',
      value:
        stock.fiftyTwoWeekLow != null && stock.fiftyTwoWeekHigh != null
          ? `$${stock.fiftyTwoWeekLow.toFixed(2)} - $${stock.fiftyTwoWeekHigh.toFixed(2)}`
          : 'N/A',
    },
    { label: 'Volume', value: formatVolume(stock.volume) },
    { label: 'Avg Volume', value: formatVolume(stock.avgVolume) },
    { label: 'Open', value: stock.open != null ? `$${formatNumber(stock.open)}` : 'N/A' },
    {
      label: 'Prev Close',
      value: stock.previousClose != null ? `$${formatNumber(stock.previousClose)}` : 'N/A',
    },
  ]

  return (
    <div className={styles.page}>
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.headerTop}>
          <span className={styles.symbolBadge}>{stock.symbol}</span>
          <span className={styles.companyName}>{stock.name}</span>
          {stock.sector && (
            <span className={styles.sectorLabel}>
              {stock.sector} · {stock.industry}
            </span>
          )}
        </div>
        <div className={styles.priceSection}>
          <span className={styles.currentPrice}>
            ${formatNumber(stock.price)}
          </span>
          <span className={`${styles.priceChange} ${stock.change >= 0 ? styles.up : styles.down}`}>
            {formatChange(stock.change, stock.changePct)}
          </span>
        </div>
      </div>

      {/* Chart */}
      <div className={styles.chartSection}>
        <MarketChart
          data={chart}
          activePeriod={period}
          onPeriodChange={handlePeriodChange}
          isLoading={chartLoading}
          title={stock.symbol}
          periods={PERIODS}
        />
      </div>

      {/* Key Stats */}
      <h2 className={styles.sectionTitle}>Key Stats</h2>
      <div className={styles.statsGrid}>
        {stats.map((stat) => (
          <div key={stat.label} className={styles.statCard}>
            <span className={styles.statLabel}>{stat.label}</span>
            <span className={styles.statValue}>{stat.value}</span>
          </div>
        ))}
      </div>

      {/* About */}
      {stock.longBusinessSummary && (
        <div className={styles.aboutCard}>
          <h2 className={styles.sectionTitle}>About {stock.name}</h2>
          <p className={styles.description}>{stock.longBusinessSummary}</p>
        </div>
      )}
    </div>
  )
}
