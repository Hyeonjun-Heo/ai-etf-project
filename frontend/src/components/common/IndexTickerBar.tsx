import { useRef, useState, useEffect, useCallback } from 'react'
import MiniLineChart from '../charts/MiniLineChart'
import type { IndexQuote, IndexSparklines } from '../../types/market'
import styles from './IndexTickerBar.module.css'

interface Props {
  indices: IndexQuote[]
  sparklines: IndexSparklines
  isLoading?: boolean
}

export default function IndexTickerBar({ indices, sparklines, isLoading }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const [showLeft, setShowLeft] = useState(false)
  const [showRight, setShowRight] = useState(false)

  const checkArrows = useCallback(() => {
    const el = scrollRef.current
    if (!el) return
    setShowLeft(el.scrollLeft > 0)
    setShowRight(el.scrollLeft + el.clientWidth < el.scrollWidth - 1)
  }, [])

  useEffect(() => {
    checkArrows()
    const el = scrollRef.current
    if (!el) return
    el.addEventListener('scroll', checkArrows)
    window.addEventListener('resize', checkArrows)
    return () => {
      el.removeEventListener('scroll', checkArrows)
      window.removeEventListener('resize', checkArrows)
    }
  }, [checkArrows, indices])

  const scroll = (dir: 'left' | 'right') => {
    const el = scrollRef.current
    if (!el) return
    const amount = 240
    el.scrollBy({ left: dir === 'left' ? -amount : amount, behavior: 'smooth' })
  }

  const formatPrice = (price: number, symbol: string) => {
    if (symbol === 'KRW=X') {
      return `${price.toLocaleString('ko-KR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}원`
    }
    return price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  }

  const formatChange = (change: number, pct: number) => {
    const sign = change >= 0 ? '+' : ''
    return `${sign}${change.toFixed(2)} (${sign}${pct.toFixed(2)}%)`
  }

  if (isLoading) {
    return (
      <div className={styles.wrapper}>
        <div className={styles.scrollContainer}>
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className={styles.skeletonItem} />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className={styles.wrapper}>
      <button
        className={`${styles.arrowBtn} ${styles.arrowLeft} ${!showLeft ? styles.arrowHidden : ''}`}
        onClick={() => scroll('left')}
        aria-label="Scroll left"
      >
        ‹
      </button>

      <div ref={scrollRef} className={styles.scrollContainer}>
        {indices.map((idx) => {
          const sparkline = sparklines[idx.symbol]
          const points = sparkline?.points ?? []
          const previousClose = sparkline?.previousClose ?? null
          const color = idx.change >= 0 ? 'var(--color-success)' : 'var(--color-danger)'

          return (
            <div key={idx.symbol} className={styles.tickerItem}>
              <div className={styles.info}>
                <span className={styles.name}>{idx.name}</span>
                <div className={styles.priceRow}>
                  <span className={styles.price}>{formatPrice(idx.price, idx.symbol)}</span>
                </div>
                <span className={`${styles.change} ${idx.change >= 0 ? styles.up : styles.down}`}>
                  {formatChange(idx.change, idx.changePct)}
                </span>
              </div>
              {points.length > 0 && (
                <div className={styles.sparkline}>
                  <MiniLineChart data={points} color={color} height={32} previousClose={previousClose} />
                </div>
              )}
            </div>
          )
        })}
      </div>

      <button
        className={`${styles.arrowBtn} ${styles.arrowRight} ${!showRight ? styles.arrowHidden : ''}`}
        onClick={() => scroll('right')}
        aria-label="Scroll right"
      >
        ›
      </button>
    </div>
  )
}
