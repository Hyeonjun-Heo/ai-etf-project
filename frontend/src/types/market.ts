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
