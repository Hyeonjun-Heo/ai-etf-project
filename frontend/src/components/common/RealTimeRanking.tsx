import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import apiClient from '../../api/client'
import type { RankingItem } from '../../types/market'
import styles from './RealTimeRanking.module.css'

type SortKey = 'amount' | 'volume' | 'rise' | 'fall'
type MarketKey = 'all' | 'domestic' | 'overseas'

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

export default function RealTimeRanking() {
  const [market, setMarket] = useState<MarketKey>('all')
  const [sort, setSort] = useState<SortKey>('amount')
  const [items, setItems] = useState<RankingItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      setLoading(true)
      try {
        const params = new URLSearchParams({ sort, category: market, limit: '100' })
        const { data } = await apiClient.get<RankingItem[]>(`/market/ranking?${params}`)
        if (!cancelled) setItems(data)
      } catch {
        if (!cancelled) setItems([])
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [market, sort])

  const formatPrice = (item: RankingItem) => {
    const isOverseas = item.market === 'overseas'
    return isOverseas
      ? `$${item.price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
      : `${item.price.toLocaleString()}원`
  }

  const formatAmount = (v: number | null) => {
    if (v == null) return '—'
    if (v >= 1_000_000_000_000) return `${(v / 1_000_000_000_000).toFixed(1)}조`
    if (v >= 100_000_000) return `${(v / 100_000_000).toFixed(0)}억`
    if (v >= 10_000) return `${(v / 10_000).toFixed(0)}만`
    return v.toLocaleString()
  }

  const formatVolume = (v: number | null) => {
    if (v == null) return '—'
    if (v >= 100_000_000) return `${(v / 100_000_000).toFixed(1)}억`
    if (v >= 10_000) return `${(v / 10_000).toFixed(0)}만`
    return v.toLocaleString()
  }

  const secondaryLabel = sort === 'volume' ? '거래량' : '거래대금'
  const secondaryValue = (item: RankingItem) =>
    sort === 'volume' ? formatVolume(item.volume) : formatAmount(item.amount)

  const handleMarketChange = (key: MarketKey) => {
    setMarket(key)
    setSort('amount')
  }

  return (
    <div className={styles.card}>
      {/* ── 헤더 영역: 마켓 탭 + 정렬 칩 ── */}
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
              onClick={() => setSort(c.key)}
            >
              {c.label}
            </button>
          ))}
        </div>
      </div>

      {/* ── 랭킹 테이블 ── */}
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
            ? Array.from({ length: 15 }).map((_, i) => (
                <tr key={i}>
                  <td colSpan={5}><div className={styles.skeletonRow} /></td>
                </tr>
              ))
            : items.map((item, idx) => (
                <tr key={`${item.symbol}-${idx}`} className={styles.row}>
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
                    {item.changePct >= 0 ? '+' : ''}{item.changePct.toFixed(2)}%
                  </td>
                  <td className={styles.numCol}>{secondaryValue(item)}</td>
                </tr>
              ))}
        </tbody>
      </table>
    </div>
  )
}
