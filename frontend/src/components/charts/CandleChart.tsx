import { useEffect, useRef } from 'react'
import { ColorType, CrosshairMode, TickMarkType, createChart } from 'lightweight-charts'
import type { ISeriesApi, IChartApi, Time } from 'lightweight-charts'
import type { ChartPoint, LiveCandle } from '../../types/market'

type TimeFrame = '1d' | 'daily' | 'weekly' | 'monthly' | 'yearly'
type CandleInterval = 'minute' | 'daily' | 'weekly' | 'monthly' | 'yearly'

interface Props {
  data: ChartPoint[]
  height?: number
  showVolume?: boolean
  candleInterval?: CandleInterval
  timeFrame?: TimeFrame
  liveCandle?: LiveCandle | null
  currencyMode?: 'krw' | 'usd'
  exchangeRate?: number
}

/** 일봉 데이터를 주봉으로 집계 (trailing 7일 — 오늘 기준 역산)
 *  버킷 키 = 각 7일 구간의 마지막 날짜 (오늘, 오늘-7, 오늘-14, ...)
 */
function aggregateWeekly(data: ChartPoint[]): ChartPoint[] {
  if (data.length === 0) return []
  const now = new Date()
  const todayMs = Date.UTC(now.getFullYear(), now.getMonth(), now.getDate())

  const buckets = new Map<string, ChartPoint>()
  for (const d of data) {
    const dateMs = new Date(d.date + 'T00:00:00Z').getTime()
    const diffMs = todayMs - dateMs
    if (diffMs < 0) continue
    const bucketIdx = Math.floor(diffMs / (7 * 86_400_000))
    const endMs = todayMs - bucketIdx * 7 * 86_400_000
    const key = new Date(endMs).toISOString().slice(0, 10)

    if (!buckets.has(key)) {
      buckets.set(key, { ...d, date: key })
    } else {
      const b = buckets.get(key)!
      b.high = Math.max(b.high ?? b.close, d.high ?? d.close)
      b.low = Math.min(b.low ?? b.close, d.low ?? d.close)
      b.close = d.close
      b.volume = (b.volume ?? 0) + (d.volume ?? 0)
    }
  }
  return Array.from(buckets.values()).sort((a, b) => a.date.localeCompare(b.date))
}

/** 일봉 데이터를 월봉으로 집계 (trailing 30일 — 오늘 기준 역산)
 *  버킷 키 = 각 30일 구간의 마지막 날짜 (오늘, 오늘-30, 오늘-60, ...)
 */
function aggregateMonthly(data: ChartPoint[]): ChartPoint[] {
  if (data.length === 0) return []
  const now = new Date()
  const todayMs = Date.UTC(now.getFullYear(), now.getMonth(), now.getDate())

  const buckets = new Map<string, ChartPoint>()
  for (const d of data) {
    const dateMs = new Date(d.date + 'T00:00:00Z').getTime()
    const diffMs = todayMs - dateMs
    if (diffMs < 0) continue
    const bucketIdx = Math.floor(diffMs / (30 * 86_400_000))
    const endMs = todayMs - bucketIdx * 30 * 86_400_000
    const key = new Date(endMs).toISOString().slice(0, 10)

    if (!buckets.has(key)) {
      buckets.set(key, { ...d, date: key })
    } else {
      const b = buckets.get(key)!
      b.high = Math.max(b.high ?? b.close, d.high ?? d.close)
      b.low = Math.min(b.low ?? b.close, d.low ?? d.close)
      b.close = d.close
      b.volume = (b.volume ?? 0) + (d.volume ?? 0)
    }
  }
  return Array.from(buckets.values()).sort((a, b) => a.date.localeCompare(b.date))
}

/** 일봉 데이터를 연봉으로 집계 (trailing 365일 — 오늘 기준 역산)
 *  버킷 키 = 각 365일 구간의 마지막 날짜 (오늘, 오늘-365, 오늘-730, ...)
 */
function aggregateYearly(data: ChartPoint[]): ChartPoint[] {
  if (data.length === 0) return []
  const now = new Date()
  const todayMs = Date.UTC(now.getFullYear(), now.getMonth(), now.getDate())

  const buckets = new Map<string, ChartPoint>()
  for (const d of data) {
    const dateMs = new Date(d.date + 'T00:00:00Z').getTime()
    const diffMs = todayMs - dateMs
    if (diffMs < 0) continue
    const bucketIdx = Math.floor(diffMs / (365 * 86_400_000))
    const endMs = todayMs - bucketIdx * 365 * 86_400_000
    const key = new Date(endMs).toISOString().slice(0, 10)

    if (!buckets.has(key)) {
      buckets.set(key, { ...d, date: key })
    } else {
      const b = buckets.get(key)!
      b.high = Math.max(b.high ?? b.close, d.high ?? d.close)
      b.low = Math.min(b.low ?? b.close, d.low ?? d.close)
      b.close = d.close
      b.volume = (b.volume ?? 0) + (d.volume ?? 0)
    }
  }
  return Array.from(buckets.values()).sort((a, b) => a.date.localeCompare(b.date))
}

function applyInterval(data: ChartPoint[], interval: CandleInterval): ChartPoint[] {
  if (interval === 'weekly') return aggregateWeekly(data)
  if (interval === 'monthly') return aggregateMonthly(data)
  if (interval === 'yearly') return aggregateYearly(data)
  return data
}

/** epoch seconds(초) → KST Date */
function toKstDateFromEpochSeconds(ts: number): Date {
  const d = new Date(ts * 1000)
  return new Date(d.getTime() + 9 * 60 * 60 * 1000)
}

/**
 * 현재 시각을 interval에 맞는 봉 키로 반환
 * - minute: epoch seconds(현재 분의 초=0)  ✅ 1분봉 캔들용
 * - daily/weekly/monthly: YYYY-MM-DD(또는 월 시작일) 문자열
 */
function getCurrentBarKey(interval: CandleInterval): Time {
  const nowKst = new Date(Date.now() + 9 * 60 * 60 * 1000)

  if (interval === 'minute') {
    // 실제 UTC epoch seconds (백엔드 b.time_kst.timestamp()와 일치)
    const now = new Date()
    now.setUTCSeconds(0, 0)
    return Math.floor(now.getTime() / 1000) as Time
  }

  if (interval === 'weekly') {
    // trailing 7일: 오늘이 현재 구간의 마지막 날(버킷 키)
    return nowKst.toISOString().slice(0, 10) as Time
  }

  // monthly/yearly/daily: trailing 방식 — 오늘이 현재 구간의 마지막 날(버킷 키)
  return nowKst.toISOString().slice(0, 10) as Time
}

/** time(Time) → YYYY-MM-DD 문자열로 정규화 (비교/가드용) */
function timeToYmdString(t: Time): string {
  if (typeof t === 'string') return t.slice(0, 10)
  if (typeof t === 'number') return toKstDateFromEpochSeconds(t).toISOString().slice(0, 10)
  // BusinessDay object — { year, month, day }
  const bd = t as { year: number; month: number; day: number }
  const y = String(bd.year).padStart(4, '0')
  const m = String(bd.month).padStart(2, '0')
  const d = String(bd.day).padStart(2, '0')
  return `${y}-${m}-${d}`
}

/** 기간에 따라 X축 라벨 포맷을 바꾼다 (토스 스타일) */
function formatTick(time: Time, frame: TimeFrame, tickMarkType: TickMarkType): string {
  // 1d: minute(UTCTimestamp epoch seconds) → HH:MM (KST), 날짜 경계에서 MM/DD
  if (frame === '1d') {
    if (typeof time !== 'number') return ''
    const kst = toKstDateFromEpochSeconds(time)
    const hh = kst.getUTCHours()
    const mm = kst.getUTCMinutes()
    // lightweight-charts가 날짜 경계라고 판단한 tick → KST 날짜 표시
    if (tickMarkType <= TickMarkType.DayOfMonth) {
      const mo = String(kst.getUTCMonth() + 1).padStart(2, '0')
      const dd = String(kst.getUTCDate()).padStart(2, '0')
      return `${mo}/${dd}`
    }
    return `${String(hh).padStart(2, '0')}:${String(mm).padStart(2, '0')}`
  }

  // daily/weekly/monthly/yearly: YYYY-MM-DD (또는 BusinessDay)
  const ymd = timeToYmdString(time)

  // 연봉: YYYY 라벨
  if (frame === 'yearly') return ymd.slice(0, 4)

  const mm = ymd.slice(5, 7)
  const yy = ymd.slice(2, 4)

  // daily/weekly/monthly: 5년치 데이터 → YY-MM 라벨
  return `${yy}-${mm}`
}

export default function CandleChart({
  data,
  height = 300,
  showVolume = true,
  candleInterval = 'daily',
  timeFrame = 'daily',
  liveCandle,
  currencyMode = 'krw',
  exchangeRate = 1380,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null)

  // chart/series 인스턴스를 ref로 보관
  const chartRef = useRef<IChartApi | null>(null)
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const volSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null)

  // live update가 “엉뚱한 데이터 범위에 새 봉을 생성”하지 않도록 가드용
  const lastBarYmdRef = useRef<string | null>(null)

  // ── 1) 차트 초기화 & 데이터 로드 ─────────────────────────────
  useEffect(() => {
    if (!containerRef.current || data.length === 0) return

    const container = containerRef.current
    const aggregated = applyInterval(data, candleInterval)

    // 마지막 데이터의 날짜(ymd) 저장 (1d는 ts가 있어야 함)
    const last = aggregated[aggregated.length - 1]
    if (candleInterval === 'minute') {
      // minute은 ts(epoch seconds)가 들어오는 걸 전제로 함
      const ts = typeof last?.ts === 'number' ? last.ts : undefined
      lastBarYmdRef.current = ts ? toKstDateFromEpochSeconds(ts).toISOString().slice(0, 10) : null
    } else {
      lastBarYmdRef.current = last?.date ? last.date.slice(0, 10) : null
    }

    // 이전 차트 정리
    chartRef.current?.remove()
    candleSeriesRef.current = null
    volSeriesRef.current = null

    const chart = createChart(container, {
      layout: {
        background: { type: ColorType.Solid, color: '#111827' },
        textColor: '#6b7280',
        fontSize: 11,
      },
      grid: {
        vertLines: { color: '#1f2937' },
        horzLines: { color: '#1f2937' },
      },
      crosshair: { mode: CrosshairMode.Magnet },
      rightPriceScale: { borderVisible: false },
      localization: {
        timeFormatter: (t: Time) => {
          if (typeof t === 'number') {
            const kst = toKstDateFromEpochSeconds(t)
            const yyyy = kst.getUTCFullYear()
            const mo = String(kst.getUTCMonth() + 1).padStart(2, '0')
            const dd = String(kst.getUTCDate()).padStart(2, '0')
            const hh = String(kst.getUTCHours()).padStart(2, '0')
            const mm = String(kst.getUTCMinutes()).padStart(2, '0')
            return `${yyyy}-${mo}-${dd} ${hh}:${mm}`
          }
          return timeToYmdString(t)
        },
      },
      timeScale: {
        borderVisible: false,
        tickMarkFormatter: (t: Time, type: TickMarkType) => formatTick(t, timeFrame, type),
      },
      width: container.clientWidth,
      height,
    })
    chartRef.current = chart

    const activeFormatter = currencyMode === 'usd'
      ? (price: number) => `$${price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
      : (price: number) => `₩${Math.round(price * exchangeRate).toLocaleString('ko-KR')}`
    const candleSeries = chart.addCandlestickSeries({
      upColor: '#22c55e',
      downColor: '#ef4444',
      borderUpColor: '#22c55e',
      borderDownColor: '#ef4444',
      wickUpColor: '#22c55e',
      wickDownColor: '#ef4444',
      priceFormat: {
        type: 'custom',
        formatter: activeFormatter,
      },
    })
    candleSeriesRef.current = candleSeries

    if (showVolume) {
      candleSeries.priceScale().applyOptions({
        scaleMargins: { top: 0.05, bottom: 0.28 },
      })
    }

    // ✅ time은 minute이면 d.ts(epoch seconds), 그 외에는 d.date(YYYY-MM-DD)를 사용
    candleSeries.setData(
      aggregated.map((d) => {
        const ts = typeof d.ts === 'number' ? d.ts : undefined
        const time: Time = candleInterval === 'minute' ? (ts as Time) : (d.date as Time)

        return {
          time,
          open: d.open ?? d.close,
          high: d.high ?? d.close,
          low: d.low ?? d.close,
          close: d.close,
        }
      })
    )

    if (showVolume && aggregated.some((d) => (d.volume ?? 0) > 0)) {
      const volSeries = chart.addHistogramSeries({
        priceFormat: { type: 'volume' },
        priceScaleId: '',
      })
      volSeries.priceScale().applyOptions({
        scaleMargins: { top: 0.8, bottom: 0 },
      })

      volSeries.setData(
        aggregated.map((d) => {
          const ts = typeof d.ts === 'number' ? d.ts : undefined
          const time: Time = candleInterval === 'minute' ? (ts as Time) : (d.date as Time)

          return {
            time,
            value: d.volume ?? 0,
            color: (d.close ?? 0) >= (d.open ?? d.close ?? 0)
              ? 'rgba(34,197,94,0.35)'
              : 'rgba(239,68,68,0.35)',
          }
        })
      )
      volSeriesRef.current = volSeries
    }

    chart.timeScale().applyOptions({ rightOffset: 3 })
    chart.timeScale().scrollToRealTime()

    const ro = new ResizeObserver(() => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth })
      }
    })
    ro.observe(container)

    return () => {
      ro.disconnect()
      chart.remove()
      chartRef.current = null
      candleSeriesRef.current = null
      volSeriesRef.current = null
      lastBarYmdRef.current = null
    }
  }, [data, height, showVolume, candleInterval, timeFrame, currencyMode, exchangeRate])

  // ── 2) 실시간 봉 업데이트 (liveCandle 변경 시만 — 차트 재생성 없음) ──
  useEffect(() => {
    if (!liveCandle || !candleSeriesRef.current) return

    const barKey = getCurrentBarKey(candleInterval)

    // ✅ 가드: 히스토리 범위를 크게 벗어난 “먼 미래 봉 생성” 방지
    // (기간 전환/종목 전환 타이밍에 엉뚱한 봉이 추가되는 현상 방지)
    // 단, 오늘(당일) 봉은 허용 — 히스토리 마지막 봉이 어제여도 오늘 봉은 생성돼야 정상
    const lastYmd = lastBarYmdRef.current
    if (lastYmd) {
      const barYmd = timeToYmdString(barKey)
      const diffDays = (new Date(barYmd).getTime() - new Date(lastYmd).getTime()) / 86_400_000
      if (diffDays > 7) return
    }

    candleSeriesRef.current.update({
      time: barKey,
      open: liveCandle.open,
      high: liveCandle.high,
      low: liveCandle.low,
      close: liveCandle.price,
    })

    if (volSeriesRef.current && liveCandle.volume > 0) {
      volSeriesRef.current.update({
        time: barKey,
        value: liveCandle.volume,
        color: liveCandle.price >= liveCandle.open
          ? 'rgba(34,197,94,0.35)'
          : 'rgba(239,68,68,0.35)',
      })
    }
  }, [liveCandle, candleInterval])

  return <div ref={containerRef} style={{ width: '100%', height }} />
}