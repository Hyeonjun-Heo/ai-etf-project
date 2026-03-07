import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import apiClient from '../../api/client'
import CandleChart from '../charts/CandleChart'
import type { ChartPoint, IndexQuote, RankingItem } from '../../types/market'
import styles from './RealTimeRanking.module.css'

type SortKey = 'amount' | 'volume' | 'rise' | 'fall'
type MarketKey = 'all' | 'domestic' | 'overseas'
type Currency = 'krw' | 'usd'

const MARKET_TABS: { key: MarketKey; label: string }[] = [
  { key: 'all',      label: '전체' },
  { key: 'domestic', label: '국내' },
  { key: 'overseas', label: '해외' },
]

const SORT_CHIPS: { key: SortKey; label: string }[] = [
  { key: 'amount', label: '거래대금' },
  { key: 'volume', label: '거래량' },
  { key: 'rise',   label: '급상승' },
  { key: 'fall',   label: '급하락' },
]

const EXCD_LABEL: Record<string, string> = {
  NAS: 'NASDAQ',
  NYS: 'NYSE',
}


function formatAmount(v: number | null) {
  if (v == null) return '—'
  if (v >= 1_000_000_000_000) return `${(v / 1_000_000_000_000).toFixed(1)}조`
  if (v >= 100_000_000) return `${(v / 100_000_000).toFixed(0)}억`
  if (v >= 10_000) return `${(v / 10_000).toFixed(0)}만`
  return v.toLocaleString()
}

function formatVolume(v: number | null) {
  if (v == null) return '—'
  if (v >= 100_000_000) return `${(v / 100_000_000).toFixed(1)}억`
  if (v >= 10_000) return `${(v / 10_000).toFixed(0)}만`
  return v.toLocaleString()
}

export default function RealTimeRanking() {
  const [market, setMarket] = useState<MarketKey>('all')
  const [sort, setSort] = useState<SortKey>('amount')
  const [items, setItems] = useState<RankingItem[]>([])
  const [loading, setLoading] = useState(true)
  const [currency, setCurrency] = useState<Currency>('krw')
  const [usdToKrw, setUsdToKrw] = useState<number>(1350)

  // Hover chart state
  const [hoveredItem, setHoveredItem] = useState<RankingItem | null>(null)
  const [hoverChart, setHoverChart] = useState<ChartPoint[]>([])
  const [hoverLoading, setHoverLoading] = useState(false)

  const chartCacheRef = useRef<Map<string, ChartPoint[]>>(new Map())
  const hoverTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const currentSymbolRef = useRef<string | null>(null)
  const mountedRef = useRef(true)

  const MAX_CHART_CACHE = 30
  const RANKING_LIMIT = 50

  // 언마운트 정리 (타이머/상태 업데이트 방지)
  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
      if (hoverTimerRef.current) clearTimeout(hoverTimerRef.current)
    }
  }, [])

  // USD/KRW 환율 조회
  useEffect(() => {
    apiClient.get<IndexQuote[]>('/market/indices').then(({ data }) => {
      const fx = data.find((q) => q.symbol === 'USD/KRW')
      if (fx && fx.price > 0) setUsdToKrw(fx.price)
    }).catch(() => {})
  }, [])

  useEffect(() => {
    let cancelled = false

    const load = async () => {
      setLoading(true)
      try {
        const params = new URLSearchParams({
          sort,
          category: market,
          limit: String(RANKING_LIMIT),
        })
        const { data } = await apiClient.get<RankingItem[]>(`/market/ranking?${params}`)
        if (!cancelled) setItems(data)
      } catch {
        if (!cancelled) setItems([])
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [market, sort])

  const handleMarketChange = useCallback((key: MarketKey) => {
    setMarket(key)
    setSort('amount')
  }, [])

  const handleSortChange = useCallback((key: SortKey) => {
    setSort(key)
  }, [])

  const handleRowLeave = useCallback(() => {
    if (hoverTimerRef.current) clearTimeout(hoverTimerRef.current)
  }, [])

  const formatPrice = useCallback((item: RankingItem) => {
    const isOverseas = item.market === 'overseas'
    if (isOverseas && currency === 'usd') {
      return `$${item.price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
    }
    if (isOverseas && currency === 'krw') {
      return `${Math.round(item.price * usdToKrw).toLocaleString()}원`
    }
    return `${Math.round(item.price).toLocaleString()}원`
  }, [currency, usdToKrw])

  const secondaryLabel = useMemo(() => (sort === 'volume' ? '거래량' : '거래대금'), [sort])

  const secondaryValue = useCallback(
    (item: RankingItem) => (sort === 'volume' ? formatVolume(item.volume) : formatAmount(item.amount)),
    [sort]
  )

  const skeletonRows = useMemo(
    () =>
      Array.from({ length: 15 }).map((_, i) => (
        <tr key={i}>
          <td colSpan={5}>
            <div className={styles.skeletonRow} />
          </td>
        </tr>
      )),
    [styles.skeletonRow]
  )

  const handleRowEnter = useCallback(
    (item: RankingItem) => {
      if (hoverTimerRef.current) clearTimeout(hoverTimerRef.current)

      const fetchForSymbol = item.symbol
      hoverTimerRef.current = setTimeout(async () => {
        currentSymbolRef.current = fetchForSymbol
        if (!mountedRef.current) return

        setHoveredItem(item)

        const cached = chartCacheRef.current.get(fetchForSymbol)
        if (cached) {
          setHoverChart(cached)
          return
        }

        setHoverLoading(true)
        setHoverChart([])

        try {
          const excdParam = item.exchange ? `&excd=${item.exchange}` : ''
          const { data } = await apiClient.get<ChartPoint[]>(
            `/market/chart?symbol=${fetchForSymbol}&period=1y${excdParam}`
          )

          // LRU-lite: 사이즈 제한
          chartCacheRef.current.set(fetchForSymbol, data)
          if (chartCacheRef.current.size > MAX_CHART_CACHE) {
            const firstKey = chartCacheRef.current.keys().next().value
            if (firstKey !== undefined) {
              chartCacheRef.current.delete(firstKey)
}
          }

          if (mountedRef.current && currentSymbolRef.current === fetchForSymbol) {
            setHoverChart(data)
          }
        } catch {
          if (mountedRef.current && currentSymbolRef.current === fetchForSymbol) {
            setHoverChart([])
          }
        } finally {
          if (mountedRef.current && currentSymbolRef.current === fetchForSymbol) {
            setHoverLoading(false)
          }
        }
      }, 150)
    },
    []
  )

  return (
    <div className={styles.card}>
      {/* ── 섹션 타이틀 ── */}
      <div className={styles.cardTitleRow}>
        <h2 className={styles.cardTitle}>실시간 차트</h2>
      </div>

      {/* ── 헤더 영역: 마켓 탭 + 정렬 칩 + 통화 토글 ── */}
      <div className={styles.controls}>
        {/* 전체 | 국내 | 해외 */}
        <div className={styles.marketTabs}>
          {MARKET_TABS.map((t) => (
            <button
              key={t.key}
              className={`${styles.marketTab} ${market === t.key ? styles.marketTabActive : ''}`}
              onClick={() => handleMarketChange(t.key)}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* 거래대금 | 거래량 | 급상승 | 급하락 */}
        <div className={styles.sortChips}>
          {SORT_CHIPS.map((c) => (
            <button
              key={c.key}
              className={`${styles.sortChip} ${sort === c.key ? styles.sortChipActive : ''}`}
              onClick={() => handleSortChange(c.key)}
            >
              {c.label}
            </button>
          ))}
        </div>

        {/* 원 / 달러 토글 */}
        <div className={styles.currencyToggle}>
          <button
            className={`${styles.currencyBtn} ${currency === 'krw' ? styles.currencyBtnActive : ''}`}
            onClick={() => setCurrency('krw')}
          >
            원
          </button>
          <button
            className={`${styles.currencyBtn} ${currency === 'usd' ? styles.currencyBtnActive : ''}`}
            onClick={() => setCurrency('usd')}
          >
            달러
          </button>
        </div>
      </div>

      {/* ── 투 패널 레이아웃 ── */}
      <div className={styles.twoPanel}>
        {/* ── 왼쪽: 랭킹 테이블 ── */}
        <div className={styles.tablePanel}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th className={styles.rankCol}>순위</th>
                <th>종목</th>
                <th className={styles.numCol}>현재가</th>
                <th className={styles.numCol}>등락률</th>
                <th className={styles.numCol}>{secondaryLabel}</th>
              </tr>
            </thead>
            <tbody>
              {loading
                ? skeletonRows
                : items.map((item, idx) => (
                    <tr
                      key={`${item.symbol}-${idx}`}
                      className={`${styles.row} ${hoveredItem?.symbol === item.symbol ? styles.rowActive : ''}`}
                      onMouseEnter={() => handleRowEnter(item)}
                      onMouseLeave={handleRowLeave}
                    >
                      <td className={styles.rank}>{idx + 1}</td>
                      <td>
                        <Link to={`/stock/${item.symbol}`} className={styles.symbolLink}>
                          {item.name || item.symbol}
                        </Link>
                        <span className={styles.symbolSub}>
                          {item.symbol}
                          {item.exchange && (
                            <span className={styles.exchangeBadge}>
                              {EXCD_LABEL[item.exchange] ?? item.exchange}
                            </span>
                          )}
                        </span>
                      </td>
                      <td className={styles.numCol}>{formatPrice(item)}</td>
                      <td className={`${styles.numCol} ${item.changePct >= 0 ? styles.up : styles.down}`}>
                        {item.changePct >= 0 ? '+' : ''}
                        {item.changePct.toFixed(2)}%
                      </td>
                      <td className={styles.numCol}>{secondaryValue(item)}</td>
                    </tr>
                  ))}
            </tbody>
          </table>
        </div>

        {/* ── 오른쪽: 호버 차트 패널 ── */}
        {hoveredItem ? (
          <div className={styles.chartPanel}>
            {/* 종목 정보 헤더 */}
            <div className={styles.chartPanelHeader}>
              <div className={styles.chartPanelInfo}>
                <div className={styles.chartPanelName}>{hoveredItem.name || hoveredItem.symbol}</div>
                <div className={styles.chartPanelPrice}>
                  {formatPrice(hoveredItem)}
                  <span className={hoveredItem.changePct >= 0 ? styles.up : styles.down}>
                    &nbsp;{hoveredItem.changePct >= 0 ? '+' : ''}
                    {hoveredItem.changePct.toFixed(2)}%
                  </span>
                </div>
              </div>
              <span className={styles.periodBadge}>주봉</span>
            </div>

            {/* 차트 영역 */}
            <div className={styles.chartArea}>
              {hoverLoading ? (
                <div className={styles.chartSkeleton} />
              ) : hoverChart.length === 0 ? (
                <div className={styles.chartEmpty}>데이터를 불러올 수 없습니다</div>
              ) : (
                <CandleChart data={hoverChart} height={220} showVolume={false} />
              )}
            </div>
          </div>
        ) : (
          <div className={styles.chartPanelEmpty}>
            <p>
              종목 위에 마우스를 올리면
              <br />
              1년 주봉 차트를 볼 수 있습니다
            </p>
          </div>
        )}
      </div>
    </div>
  )
}