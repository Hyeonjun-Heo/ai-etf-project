import { NavLink, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../stores/authStore'
import styles from './TopNav.module.css'

const menuItems = [
  { to: '/', label: 'Home' },
  { to: '/portfolio', label: 'Portfolio' },
  { to: '/backtest', label: 'Backtest' },
  { to: '/simulation', label: 'Simulation' },
  { to: '/settings', label: 'Settings' },
]

export default function TopNav() {
  const navigate = useNavigate()
  const { isAuthenticated, user, logout } = useAuthStore()

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
        {isAuthenticated ? (
          <div className={styles.userInfo}>
            <span className={styles.username}>{user?.username}</span>
            <button className={styles.logoutBtn} onClick={handleLogout}>
              Logout
            </button>
          </div>
        ) : (
          <button
            className={styles.loginBtn}
            onClick={() => navigate('/login')}
          >
            Login
          </button>
        )}
      </div>
    </nav>
  )
}
