export interface IndexQuote {
  symbol: string
  name: string
  price: number
  change: number
  changePct: number
}

export interface EtfQuote {
  symbol: string
  name: string
  price: number
  change: number
  changePct: number
}

export interface ChartPoint {
  date: string
  close: number
  open?: number
  high?: number
  low?: number
  volume?: number
  ts?: number   // epoch seconds (인트라데이 분봉용)
}

export interface Movers {
  gainers: MoverItem[]
  losers: MoverItem[]
}

export interface MoverItem {
  symbol: string
  price: number
  change: number
  changePct: number
}

export interface IndexSparklineData {
  points: ChartPoint[]
  previousClose: number | null
}

export type IndexSparklines = Record<string, IndexSparklineData>

export interface RankingItem {
  symbol: string
  name: string
  price: number
  change: number
  changePct: number
  volume: number | null
  amount: number | null
  exchange?: string
  market?: 'domestic' | 'overseas'
}

export interface LiveCandle {
  time: string       // "HH:MM" (국내 1D) | "" (해외)
  price: number
  open: number
  high: number
  low: number
  volume: number
  change: number
  changePct: number
}

export interface SearchResult {
  symbol: string
  name: string
  type: 'equity' | 'etf'
  market: 'domestic' | 'overseas'
  exchange: string
}

export interface WatchlistItem {
  symbol: string
  name: string
  market: 'domestic' | 'overseas'
  added_at: string
}

export interface StockDetail {
  symbol: string
  name: string
  price: number
  change: number
  changePct: number
  marketCap: number | null
  peRatio: number | null
  dividendYield: number | null
  fiftyTwoWeekHigh: number | null
  fiftyTwoWeekLow: number | null
  volume: number | null
  avgVolume: number | null
  open: number | null
  previousClose: number | null
  sector: string
  industry: string
  longBusinessSummary: string
}
