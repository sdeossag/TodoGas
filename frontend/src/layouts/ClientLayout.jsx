import { useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import useAuthStore from '../store/authStore'

const NAV_LINKS = [
  { to: '/mis-dashboard', label: 'Dashboard' },
  { to: '/mis-activos', label: 'Mis activos' },
  { to: '/mis-reportes', label: 'Mis reportes' },
]

export default function ClientLayout() {
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()
  const [showLogo, setShowLogo] = useState(true)

  const handleLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-brand text-white px-6 h-16 flex items-center justify-between shadow">
        {showLogo ? (
          <img
            src="/logo-invertido-.png"
            alt="TodoGas CMMS"
            className="h-9 w-auto"
            onError={() => setShowLogo(false)}
          />
        ) : (
          <span className="font-bold text-base">TodoGas CMMS</span>
        )}
        <div className="flex items-center gap-6">
          <nav className="flex gap-4">
            {NAV_LINKS.map(({ to, label }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `text-sm font-medium transition-colors ${isActive ? 'text-white underline' : 'text-brand-200 hover:text-white'}`
                }
              >
                {label}
              </NavLink>
            ))}
          </nav>
          <div className="flex items-center gap-3">
            <span className="text-sm text-brand-200">{user?.first_name}</span>
            <button
              onClick={handleLogout}
              className="text-xs text-brand-200 hover:text-white transition-colors"
            >
              Salir
            </button>
          </div>
        </div>
      </header>
      <main className="max-w-5xl mx-auto py-8 px-4">
        <Outlet />
      </main>
    </div>
  )
}
