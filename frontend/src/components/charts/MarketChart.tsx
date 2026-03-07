import { useEffect, useRef, useState } from 'react'
import type { ChartPoint, LiveCandle } from '../../types/market'
import CandleChart from './CandleChart'
import styles from './MarketChart.module.css'

const DEFAULT_PERIODS = ['1d', 'daily', 'weekly', 'monthly', 'yearly'] as const

const PERIOD_LABEL: Record<string, string> = {
  '1d':      '분봉',
  'daily':   '일',
  'weekly':  '주',
  'monthly': '월',
  'yearly':  '연',
}

const MINUTE_INTERVALS = [1, 3, 5, 10, 15, 30, 60, 120, 240]

interface Props {
  data: ChartPoint[]
  onPeriodChange: (period: string) => void
  activePeriod: string
  isLoading?: boolean
  title?: string
  periods?: readonly string[]
  liveCandle?: LiveCandle | null
  minuteInterval?: number
  onIntervalChange?: (interval: number) => void
  currencyMode?: 'krw' | 'usd'
  exchangeRate?: number
}

type CandleInterval = 'minute' | 'daily' | 'weekly' | 'monthly' | 'yearly'

function getCandleInterval(activePeriod: string): CandleInterval {
  if (activePeriod === '1d') return 'minute'
  if (activePeriod === 'weekly') return 'weekly'
  if (activePeriod === 'monthly') return 'monthly'
  if (activePeriod === 'yearly') return 'yearly'
  return 'daily'
}

export default function MarketChart({
  data,
  onPeriodChange,
  activePeriod,
  isLoading,
  title = 'S&P 500',
  periods = DEFAULT_PERIODS,
  liveCandle,
  minuteInterval = 10,
  onIntervalChange,
  currencyMode,
  exchangeRate,
}: Props) {
  const candleInterval = getCandleInterval(activePeriod)
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // 드롭다운 외부 클릭 시 닫기
  useEffect(() => {
    if (!dropdownOpen) return
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [dropdownOpen])

  const handleIntervalSelect = (v: number) => {
    onIntervalChange?.(v)
    setDropdownOpen(false)
    if (activePeriod !== '1d') onPeriodChange('1d')
  }

  const intervalLabel = minuteInterval >= 60
    ? `${minuteInterval / 60}시간`
    : `${minuteInterval}분`

  return (
    <div className={styles.wrapper}>
      <div className={styles.header}>
        <h2 className={styles.title}>{title}</h2>
        <div className={styles.periods}>

          {/* 분봉 드롭다운 — onIntervalChange 제공 시만 렌더 */}
          {onIntervalChange && (
            <div className={styles.intervalDropdown} ref={dropdownRef}>
              <button
                className={`${styles.periodBtn} ${activePeriod === '1d' ? styles.active : ''}`}
                onClick={() => setDropdownOpen(o => !o)}
              >
                {intervalLabel}
                <span className={styles.dropdownArrow}>▾</span>
              </button>
              {dropdownOpen && (
                <ul className={styles.dropdownMenu}>
                  {MINUTE_INTERVALS.map(v => (
                    <li
                      key={v}
                      className={`${styles.dropdownItem} ${v === minuteInterval && activePeriod === '1d' ? styles.dropdownItemActive : ''}`}
                      onClick={() => handleIntervalSelect(v)}
                    >
                      {v >= 60 ? `${v / 60}시간` : `${v}분`}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {/* 기간 버튼 — 드롭다운이 있으면 '1d' 버튼은 드롭다운이 대신함 */}
          {periods
            .filter(p => !(onIntervalChange && p === '1d'))
            .map((p) => (
              <button
                key={p}
                className={`${styles.periodBtn} ${activePeriod === p ? styles.active : ''}`}
                onClick={() => onPeriodChange(p)}
              >
                {PERIOD_LABEL[p] ?? p.toUpperCase()}
              </button>
            ))}
        </div>
      </div>

      <div className={styles.chartArea}>
        {isLoading ? (
          <div className={styles.skeleton} />
        ) : (
          <CandleChart
            key={`${title}-${activePeriod}-${minuteInterval}`}
            data={data}
            height={450}
            showVolume
            candleInterval={candleInterval}
            timeFrame={activePeriod}
            liveCandle={liveCandle}
            currencyMode={currencyMode}
            exchangeRate={exchangeRate}
          />
        )}
      </div>
    </div>
  )
}
