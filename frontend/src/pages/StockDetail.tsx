import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import apiClient from '../api/client'
import MarketChart from '../components/charts/MarketChart'
import WatchlistButton from '../components/common/WatchlistButton'
import { useStockRealtime } from '../hooks/useStockRealtime'
import type { ChartPoint, IndexQuote, StockDetail as StockDetailType } from '../types/market'
import styles from './StockDetail.module.css'

const PERIODS = ['1d', 'daily', 'weekly', 'monthly', 'yearly'] as const

// 버튼(Timeframe) → 백엔드에 실제로 요청할 기간
// daily/weekly/monthly/yearly 모두 5y 일봉 데이터를 받아 클라이언트에서 집계
const FETCH_PERIOD: Record<string, string> = {
  'daily':   '5y',
  'weekly':  '5y',
  'monthly': '5y',
  'yearly':  '5y',
}

export default function StockDetail() {
  const { symbol } = useParams<{ symbol: string }>()
  const isDomesticSymbol = /^\d{6}$/.test(symbol ?? '')

  const [stock, setStock] = useState<StockDetailType | null>(null)
  const [chart, setChart] = useState<ChartPoint[]>([])
  const [period, setPeriod] = useState('1d')
  const [minuteInterval, setMinuteInterval] = useState(10)
  const [loading, setLoading] = useState(true)
  const [chartLoading, setChartLoading] = useState(false)
  const [error, setError] = useState(false)
  const [showKrw, setShowKrw] = useState(true)
  const [usdKrwRate, setUsdKrwRate] = useState(1380)

  // 실시간 시세 (항상 구독 — period에 따라 사용 방식이 달라짐)
  const { liveCandle } = useStockRealtime(symbol)

// 종목 상세 정보 로드 (symbol 변경 시만)
useEffect(() => {
  if (!symbol) return
  const upperSymbol = symbol.toUpperCase()
  const load = async () => {
    setLoading(true)
    setError(false)
    try {
      const res = await apiClient.get(`/market/stock/${upperSymbol}`)
      setStock(res.data)
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }
  load()
}, [symbol])

// 차트 데이터 로드 (symbol, period, minuteInterval 변경 시)
useEffect(() => {
  if (!symbol) return
  const upperSymbol = symbol.toUpperCase()
  const fetchPeriod = FETCH_PERIOD[period] ?? period
  const intervalParam = period === '1d' ? `&interval=${minuteInterval}` : ''
  const loadChart = async () => {
    setChartLoading(true)
    setChart([])
    try {
      const res = await apiClient.get(`/market/chart?symbol=${upperSymbol}&period=${fetchPeriod}${intervalParam}`)
      setChart(res.data)
    } catch {
      // leave empty
    } finally {
      setChartLoading(false)
    }
  }
  loadChart()
}, [symbol, period, minuteInterval])

  // 1D 분봉 차트에 실시간 가격 반영 (마지막 포인트 update or append)
  useEffect(() => {
    if (!liveCandle || period !== '1d' || !liveCandle.time) return
    const minuteKey = liveCandle.time.slice(0, 5) // "HH:MM"
    setChart(prev => {
      if (!prev.length) return prev
      const last = prev[prev.length - 1]
      if (last.date === minuteKey) {
        return [...prev.slice(0, -1), { ...last, close: liveCandle.price }]
      }
      // 새 분봉 추가 시 현재 UTC epoch을 ts로 설정 (multi-day 분봉 지원)
      const ts = Math.floor(Date.now() / 1000)
      return [...prev, { date: minuteKey, ts, close: liveCandle.price }]
    })
  }, [liveCandle, period])

  // 해외 종목: USD/KRW 환율 조회
  useEffect(() => {
    if (isDomesticSymbol) return
    apiClient.get<IndexQuote[]>('/market/indices').then(res => {
      const entry = res.data.find((i: IndexQuote) => i.symbol === 'USDKRW')
      if (entry?.price) setUsdKrwRate(entry.price)
    }).catch(() => {})
  }, [isDomesticSymbol])

  const handlePeriodChange = (newPeriod: string) => {
    setChartLoading(true) // 즉시 skeleton 표시 — 기존 데이터로 CandleChart 재마운트 방지
    setPeriod(newPeriod)
  }


  // 해외 종목의 USD 가격을 표시 통화로 변환
  const conv = (val: number | null | undefined): number | null => {
    if (val == null) return null
    if (isDomesticSymbol || !showKrw) return val
    return val * usdKrwRate
  }

  const displayCurrency = isDomesticSymbol ? '₩' : (showKrw ? '₩' : '$')

  const formatChange = (change: number, pct: number) => {
    const displayChange = (!isDomesticSymbol && showKrw) ? change * usdKrwRate : change
    const prefix = displayChange >= 0 ? '+' : '-'
    const absVal = Math.abs(displayChange)
    const numStr = (isDomesticSymbol || showKrw)
      ? Math.round(absVal).toLocaleString('ko-KR')
      : absVal.toFixed(2)
    const pctPrefix = pct >= 0 ? '+' : '-'
    return `${prefix}${numStr} (${pctPrefix}${Math.abs(pct).toFixed(2)}%)`
  }

  const formatNumber = (value: number | null | undefined) => {
    if (value == null) return 'N/A'
    if (isDomesticSymbol || showKrw) {
      return value.toLocaleString('ko-KR', { maximumFractionDigits: 0 })
    }
    return value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  }

  const formatMarketCap = (value: number | null | undefined) => {
    if (value == null) return 'N/A'
    if (isDomesticSymbol) {
      // KIS 시가총액 단위: 억원
      if (value >= 10000) return `${(value / 10000).toFixed(2)}조원`
      return `${value.toLocaleString('ko-KR')}억원`
    }
    if (showKrw) {
      const krw = value * usdKrwRate
      if (krw >= 1e12) return `₩${(krw / 1e12).toFixed(2)}조`
      if (krw >= 1e8) return `₩${(krw / 1e8).toFixed(2)}억`
      return `₩${krw.toLocaleString('ko-KR')}`
    }
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
          ? `${displayCurrency}${formatNumber(conv(stock.fiftyTwoWeekLow))} - ${displayCurrency}${formatNumber(conv(stock.fiftyTwoWeekHigh))}`
          : 'N/A',
    },
    { label: 'Volume', value: formatVolume(stock.volume) },
    { label: 'Avg Volume', value: formatVolume(stock.avgVolume) },
    { label: 'Open', value: stock.open != null ? `${displayCurrency}${formatNumber(conv(stock.open))}` : 'N/A' },
    {
      label: 'Prev Close',
      value: stock.previousClose != null ? `${displayCurrency}${formatNumber(conv(stock.previousClose))}` : 'N/A',
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
          <WatchlistButton
            symbol={stock.symbol}
            name={stock.name}
            market={isDomesticSymbol ? 'domestic' : 'overseas'}
          />
          {!isDomesticSymbol && (
            <div className={styles.currencyToggle}>
              <button
                className={`${styles.currencyBtn} ${showKrw ? styles.currencyBtnActive : ''}`}
                onClick={() => setShowKrw(true)}
              >원화</button>
              <button
                className={`${styles.currencyBtn} ${!showKrw ? styles.currencyBtnActive : ''}`}
                onClick={() => setShowKrw(false)}
              >달러</button>
            </div>
          )}
        </div>
        <div className={styles.priceSection}>
          <span className={styles.currentPrice}>
            {displayCurrency}{formatNumber(conv(stock.price))}
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
          liveCandle={period === 'daily' ? liveCandle : null}
          minuteInterval={minuteInterval}
          onIntervalChange={setMinuteInterval}
          currencyMode={!isDomesticSymbol && !showKrw ? 'usd' : 'krw'}
          exchangeRate={usdKrwRate}
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
