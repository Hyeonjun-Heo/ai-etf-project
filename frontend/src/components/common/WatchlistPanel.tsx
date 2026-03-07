import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import apiClient from '../../api/client'
import { useAuthStore } from '../../stores/authStore'
import type { WatchlistItem } from '../../types/market'
import styles from './WatchlistPanel.module.css'

interface PriceData {
  price: number
  change: number
  changePct: number
}

type PriceMap = Record<string, PriceData>

export default function WatchlistPanel() {
  const user = useAuthStore((s) => s.user)
  const navigate = useNavigate()
  const [items, setItems] = useState<WatchlistItem[]>([])
  const [prices, setPrices] = useState<PriceMap>({})
  const [loading, setLoading] = useState(true)
  const [showKrw, setShowKrw] = useState(true)

  useEffect(() => {
    if (!user) { setLoading(false); return }
    apiClient.get<WatchlistItem[]>('/watchlist').then(async (res) => {
      const list = res.data
      setItems(list)
      // 가격 병렬 조회
      const results = await Promise.allSettled(
        list.map((item) => apiClient.get(`/market/stock/${item.symbol}`))
      )
      const map: PriceMap = {}
      results.forEach((r, i) => {
        if (r.status === 'fulfilled') {
          const d = r.value.data
          map[list[i].symbol] = { price: d.price, change: d.change, changePct: d.changePct }
        }
      })
      setPrices(map)
    }).catch(() => {}).finally(() => setLoading(false))
  }, [user])

  const formatPrice = (symbol: string, price: number, market: string) => {
    if (market === 'domestic') return `${Math.round(price).toLocaleString('ko-KR')}원`
    if (showKrw) return `${Math.round(price * 1380).toLocaleString('ko-KR')}원`
    return `$${price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  }

  const handleRemove = async (e: React.MouseEvent, symbol: string) => {
    e.stopPropagation()
    try {
      await apiClient.delete(`/watchlist/${symbol}`)
      setItems(prev => prev.filter(i => i.symbol !== symbol))
    } catch { /* ignore */ }
  }

  // 국내/해외 분류
  const domestic = items.filter(i => i.market === 'domestic')
  const overseas = items.filter(i => i.market === 'overseas')

  const renderItem = (item: WatchlistItem) => {
    const p = prices[item.symbol]
    const isUp = p ? p.changePct >= 0 : null
    return (
      <div key={item.symbol} className={styles.item} onClick={() => navigate(`/stock/${item.symbol}`)}>
        <div className={styles.itemLeft}>
          <div className={styles.symbolBadge}>{item.symbol.slice(0, 4)}</div>
          <div className={styles.itemInfo}>
            <div className={styles.itemName}>{item.name}</div>
            <div className={styles.itemSymbol}>{item.symbol}</div>
          </div>
        </div>
        <div className={styles.itemRight}>
          {p ? (
            <>
              <div className={styles.itemPrice}>
                {formatPrice(item.symbol, p.price, item.market)}
              </div>
              <div className={`${styles.itemChange} ${isUp ? styles.up : styles.down}`}>
                {isUp ? '+' : ''}{item.market === 'domestic' || showKrw
                  ? `${Math.round(p.change * (item.market === 'overseas' && showKrw ? 1380 : 1)).toLocaleString('ko-KR')}원`
                  : `$${Math.abs(p.change).toFixed(2)}`
                } ({isUp ? '+' : ''}{p.changePct.toFixed(2)}%)
              </div>
            </>
          ) : (
            <div className={styles.loadingPrice} />
          )}
          <button className={styles.removeBtn} onClick={(e) => handleRemove(e, item.symbol)} title="관심 해제">×</button>
        </div>
      </div>
    )
  }

  return (
    <div className={styles.panel}>
      {/* 헤더 */}
      <div className={styles.header}>
        <span className={styles.title}>관심</span>
        <div className={styles.currencyToggle}>
          <button className={`${styles.currBtn} ${showKrw ? styles.currActive : ''}`} onClick={() => setShowKrw(true)}>원</button>
          <button className={`${styles.currBtn} ${!showKrw ? styles.currActive : ''}`} onClick={() => setShowKrw(false)}>$</button>
        </div>
      </div>

      {/* 비로그인 */}
      {!user && (
        <div className={styles.empty}>
          <div className={styles.emptyIcon}>
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
            </svg>
          </div>
          <div className={styles.emptyText}>로그인 후 이용 가능합니다</div>
          <button className={styles.loginBtn} onClick={() => navigate('/login')}>로그인</button>
        </div>
      )}

      {/* 로딩 */}
      {user && loading && (
        <div className={styles.skeletonList}>
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className={styles.skeletonItem} />
          ))}
        </div>
      )}

      {/* 빈 목록 */}
      {user && !loading && items.length === 0 && (
        <div className={styles.empty}>
          <div className={styles.emptyText}>관심 종목이 없습니다</div>
          <div className={styles.emptyHint}>종목 상세 페이지에서<br />별 버튼을 눌러 추가하세요</div>
        </div>
      )}

      {/* 목록 */}
      {user && !loading && items.length > 0 && (
        <>
          {domestic.length > 0 && (
            <div className={styles.group}>
              <div className={styles.groupLabel}>국내</div>
              {domestic.map(renderItem)}
            </div>
          )}
          {overseas.length > 0 && (
            <div className={styles.group}>
              <div className={styles.groupLabel}>해외</div>
              {overseas.map(renderItem)}
            </div>
          )}
        </>
      )}
    </div>
  )
}
