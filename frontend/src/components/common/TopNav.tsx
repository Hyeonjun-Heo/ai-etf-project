import { useEffect, useRef, useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import apiClient from '../../api/client'
import { useAuthStore } from '../../stores/authStore'
import type { SearchResult } from '../../types/market'
import styles from './TopNav.module.css'

const menuItems = [
  { to: '/', label: '홈' },
  { to: '/portfolio', label: '포트폴리오' },
  { to: '/backtest', label: '백테스트' },
  { to: '/simulation', label: '시뮬레이션' },
  { to: '/settings', label: '설정' },
]

export default function TopNav() {
  const navigate = useNavigate()
  const { isAuthenticated, user, logout } = useAuthStore()

  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [isOpen, setIsOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const wrapperRef = useRef<HTMLDivElement>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // 검색어 변경 시 debounce 후 API 호출
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)

    if (query.length < 2) {
      setResults([])
      setIsOpen(false)
      return
    }

    debounceRef.current = setTimeout(async () => {
      setIsLoading(true)
      try {
        const { data } = await apiClient.get<SearchResult[]>('/market/search', {
          params: { q: query },
        })
        setResults(data)
        setIsOpen(data.length > 0)
      } catch {
        setResults([])
        setIsOpen(false)
      } finally {
        setIsLoading(false)
      }
    }, 300)

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [query])

  // 외부 클릭 시 드롭다운 닫기
  useEffect(() => {
    const handleMouseDown = (e: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleMouseDown)
    return () => document.removeEventListener('mousedown', handleMouseDown)
  }, [])

  const handleSelect = (symbol: string) => {
    setQuery('')
    setResults([])
    setIsOpen(false)
    navigate(`/stock/${symbol}`)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      setIsOpen(false)
      setQuery('')
    }
  }

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  return (
    <nav className={styles.nav}>
      <div className={styles.left}>
        <NavLink to="/" className={styles.logo}>
          <span className={styles.logoIcon}>📊</span>
          AI ETF
        </NavLink>
        <div className={styles.menu}>
          {menuItems.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `${styles.menuItem} ${isActive ? styles.menuItemActive : ''}`
              }
              end={to === '/'}
            >
              {label}
            </NavLink>
          ))}
        </div>
      </div>

      <div className={styles.right}>
        <div className={styles.searchWrapper} ref={wrapperRef}>
          <input
            className={styles.searchInput}
            type="text"
            placeholder="종목명 또는 코드 검색..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => results.length > 0 && setIsOpen(true)}
          />
          {isLoading && <span className={styles.searchSpinner} />}
          {isOpen && results.length > 0 && (
            <ul className={styles.dropdown}>
              {results.map((item) => (
                <li
                  key={item.symbol}
                  className={styles.dropdownItem}
                  onMouseDown={() => handleSelect(item.symbol)}
                >
                  <span className={styles.dropdownName}>{item.name}</span>
                  <span className={styles.dropdownSymbol}>{item.symbol}</span>
                  <span
                    className={`${styles.badge} ${
                      item.market === 'domestic' ? styles.badgeDomestic : styles.badgeOverseas
                    }`}
                  >
                    {item.market === 'domestic' ? '국내' : '해외'}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
        {isAuthenticated ? (
          <div className={styles.userInfo}>
            <span className={styles.username}>{user?.username}</span>
            <button className={styles.logoutBtn} onClick={handleLogout}>
              로그아웃
            </button>
          </div>
        ) : (
          <button
            className={styles.loginBtn}
            onClick={() => navigate('/login')}
          >
            로그인
          </button>
        )}
      </div>
    </nav>
  )
}
