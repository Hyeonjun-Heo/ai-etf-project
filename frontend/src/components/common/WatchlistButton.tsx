import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import apiClient from '../../api/client'
import { useAuthStore } from '../../stores/authStore'
import styles from './WatchlistButton.module.css'

interface Props {
  symbol: string
  name: string
  market: 'domestic' | 'overseas'
}

export default function WatchlistButton({ symbol, name, market }: Props) {
  const user = useAuthStore((s) => s.user)
  const navigate = useNavigate()
  const [inWatchlist, setInWatchlist] = useState(false)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!user) return
    apiClient.get(`/watchlist/${symbol}`)
      .then((res) => setInWatchlist(res.data.in_watchlist))
      .catch(() => {})
  }, [symbol, user])

  const handleClick = async () => {
    if (!user) {
      navigate('/login')
      return
    }
    if (loading) return
    setLoading(true)
    try {
      if (inWatchlist) {
        await apiClient.delete(`/watchlist/${symbol}`)
        setInWatchlist(false)
      } else {
        await apiClient.post('/watchlist', { symbol, name, market })
        setInWatchlist(true)
      }
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  return (
    <button
      className={`${styles.btn} ${inWatchlist ? styles.active : ''}`}
      onClick={handleClick}
      disabled={loading}
      title={inWatchlist ? '관심 종목에서 제거' : '관심 종목 추가'}
      aria-label={inWatchlist ? '관심 종목에서 제거' : '관심 종목 추가'}
    >
      <svg
        width="20"
        height="20"
        viewBox="0 0 24 24"
        fill={inWatchlist ? 'currentColor' : 'none'}
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
      </svg>
      <span>{inWatchlist ? '관심 해제' : '관심 종목'}</span>
    </button>
  )
}
